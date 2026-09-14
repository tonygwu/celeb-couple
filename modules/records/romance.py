"""Classify whether two actors' characters are a couple IN the film.

Co-appearance in a cast list is not a pairing. The pilot's 20 candidates
include films where the two names share nothing but a poster, and scoring those
as romances would put couples on a leaderboard who were never couples.

Plot text comes from Wikipedia (CC BY-SA). The classifier sees only that text
and the two actors' names: no box office, no billing order, no reviews.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

__all__ = ["RomanceVerdict", "fetch_plot", "fetch_cast", "build_prompt",
           "parse_verdict", "QUALIFYING", "PlotUnavailable", "title_for_qid"]

API = "https://en.wikipedia.org/w/api.php"
#: Imported, not copied. This file said M1 while the other five said M0.
from packages.wiki.fetch import USER_AGENT  # noqa: E402,F401

#: The only classification that produces a scorable on-screen pairing.
QUALIFYING = "reciprocal_romance"

_REF = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.S)
_MARKUP = re.compile(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]|'''|''|\{\{[^}]*\}\}")
_JSON = re.compile(r"\{.*\}", re.S)
#: "* [[Ben Affleck]] as Matt Murdock / Daredevil"
_CAST_LINE = re.compile(
    r"^\*+\s*\[\[(?!File:|Image:)([^\]|]+?)(?:\|[^\]]*)?\]\]"
    r"[^a-zA-Z]*as\s+(.+)$",
    re.M)


class PlotUnavailable(RuntimeError):
    pass


def title_for_qid(qid: str, timeout: int = 45) -> str | None:
    """Resolve the English Wikipedia article from a Wikidata id.

    WHY NOT JUST USE THE TITLE
    --------------------------
    Measured 2026-09-14: fetching by film title sent 13 of 20 candidates to the
    wrong article and reported "no Plot section" for every one. "Pearl Harbor"
    is a harbour in Hawaii, "Elektra" is a figure from Greek tragedy, and
    "Daredevil" is a comics character. Every one of those returned a real
    article with no plot, which looks exactly like a missing plot rather than
    like a wrong subject.

    The candidate records already carry the film's Wikidata id. Resolving the
    sitelink from it cannot land on a different subject.
    """
    url = (
        "https://www.wikidata.org/w/api.php?"
        + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": qid, "props": "sitelinks",
            "sitefilter": "enwiki", "format": "json",
        })
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        blob = json.load(fh)
    entity = (blob.get("entities") or {}).get(qid) or {}
    link = (entity.get("sitelinks") or {}).get("enwiki") or {}
    return link.get("title")


@dataclass(frozen=True)
class RomanceVerdict:
    work: str
    classification: str
    evidence: str
    reasoning: str
    characters: dict
    plot_sha256: str
    grounded: bool

    @property
    def qualifies(self) -> bool:
        return self.classification == QUALIFYING and self.grounded

    def as_dict(self) -> dict:
        return {
            "work": self.work, "classification": self.classification,
            "evidence": self.evidence, "reasoning": self.reasoning,
            "characters": self.characters, "plot_sha256": self.plot_sha256,
            "evidence_grounded_in_plot": self.grounded, "qualifies": self.qualifies,
        }


def _clean(wikitext: str) -> str:
    text = _REF.sub("", wikitext)
    text = _MARKUP.sub(lambda m: m.group(1) or "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def fetch_plot(page: str, timeout: int = 45) -> tuple[str, str]:
    """Return (clean plot text, sha256 of the bytes retrieved)."""
    import hashlib

    url = API + "?" + urllib.parse.urlencode({
        "action": "parse", "page": page, "prop": "sections",
        "format": "json", "formatversion": "2",
    })
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        raw = fh.read()
    sections = json.loads(raw).get("parse", {}).get("sections", [])
    idx = next(
        (s["index"] for s in sections
         if s["line"].strip().lower() in ("plot", "synopsis", "plot summary")),
        None,
    )
    if idx is None:
        raise PlotUnavailable(f"{page}: no Plot or Synopsis section")

    url = API + "?" + urllib.parse.urlencode({
        "action": "parse", "page": page, "prop": "wikitext",
        "section": str(idx), "format": "json", "formatversion": "2",
    })
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        raw2 = fh.read()
    text = _clean(json.loads(raw2)["parse"]["wikitext"])
    if len(text) < 200:
        raise PlotUnavailable(f"{page}: plot section is only {len(text)} chars")
    return text, hashlib.sha256(raw2).hexdigest()


def fetch_cast(page: str, timeout: int = 45) -> dict[str, str]:
    """Map actor -> character from the article's Cast section.

    WHY THIS IS NEEDED
    ------------------
    Measured 2026-09-14: fifteen of twenty candidates came back cannot_tell, and
    every reason was the same. A Wikipedia plot summary describes CHARACTERS and
    never names actors, so a classifier handed two actor names genuinely cannot
    tell which characters they are. The model was right to refuse; the prompt was
    wrong to ask.
    """
    url = API + "?" + urllib.parse.urlencode({
        "action": "parse", "page": page, "prop": "sections",
        "format": "json", "formatversion": "2"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        sections = json.load(fh).get("parse", {}).get("sections", [])
    idx = next((s["index"] for s in sections
                if s["line"].strip().lower() in ("cast", "cast and characters",
                                                 "casting", "voice cast")), None)
    if idx is None:
        return {}
    url = API + "?" + urllib.parse.urlencode({
        "action": "parse", "page": page, "prop": "wikitext",
        "section": str(idx), "format": "json", "formatversion": "2"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        wikitext = json.load(fh)["parse"]["wikitext"]
    body = _REF.sub("", wikitext)
    out: dict[str, str] = {}
    for actor, role in _CAST_LINE.findall(body):
        character = _MARKUP.sub(lambda m: m.group(1) or "", role).strip()
        character = re.split(r"\s+[-\u2013]\s+|,|\s+\(", character)[0]
        character = character.strip().strip("'\"* ")
        if character:
            out[actor.strip()] = character
    return out


def build_prompt(rubric: str, schema: str, work: str, a: str, b: str, plot: str,
                 cast: dict[str, str] | None = None) -> str:
    cast = cast or {}
    a_role, b_role = cast.get(a), cast.get(b)
    if a_role and b_role:
        who = ("ACTOR A: %s, who plays **%s**\n"
               "ACTOR B: %s, who plays **%s**\n\n"
               "The plot below names characters, not actors. Judge the "
               "relationship between %s and %s." % (a, a_role, b, b_role,
                                                    a_role, b_role))
    else:
        missing = a if not a_role else b
        who = ("ACTOR A: %s\nACTOR B: %s\n\n"
               "The article's cast list does not say which character %s plays, "
               "and the plot names characters rather than actors. If you cannot "
               "establish the mapping from the text, return cannot_tell."
               % (a, b, missing))
    return (
        "%s\n\n---\n\nYour output must validate against this schema:\n\n"
        "%s\n\n---\n\nFILM: %s\n%s\n\n"
        "PLOT SUMMARY (this is the only source you may use):\n\n%s\n\n"
        "---\n\nReturn the JSON object and nothing else."
        % (rubric, schema, work, who, plot)
    )


def parse_verdict(text: str, work: str, plot: str, plot_sha: str) -> RomanceVerdict:
    """Parse and GROUND the verdict: the quote must appear in the plot text.

    A classification whose evidence is not in the supplied text is a claim about
    something the model remembered, not about the film as described, and the
    rubric's rule 3 forbids it.
    """
    m = _JSON.search(text or "")
    if not m:
        raise ValueError("no JSON object in the response")
    obj = json.loads(m.group(0))
    if obj.get("schema_version") != "romance-1.0":
        raise ValueError(f"wrong schema_version {obj.get('schema_version')!r}")
    classification = obj.get("classification")
    valid = {"reciprocal_romance", "co_appearance_only", "unrequited",
             "brief_or_incidental", "family_or_platonic", "coerced_or_assault",
             "cannot_tell"}
    if classification not in valid:
        raise ValueError(f"unknown classification {classification!r}")

    evidence = (obj.get("evidence") or "").strip()
    normalise = lambda s: re.sub(r"\s+", " ", s).lower()
    grounded = bool(evidence) and normalise(evidence) in normalise(plot)
    if classification == QUALIFYING and not grounded:
        # Downgrade rather than accept: an ungrounded quote cannot support the
        # only classification that puts a couple on a leaderboard.
        classification = "cannot_tell"

    return RomanceVerdict(
        work=work, classification=classification, evidence=evidence,
        reasoning=(obj.get("reasoning") or "").strip(),
        characters=obj.get("characters") or {}, plot_sha256=plot_sha,
        grounded=grounded,
    )
