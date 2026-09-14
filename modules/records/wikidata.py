"""Relationship and birth-date ingestion from Wikidata.

Wikidata is CC0 and carries date qualifiers with an explicit precision code, so
it is the one route in this project where facts can be retained and republished
with no attribution obligation.

It is also INCOMPLETE, measured 2026-09-13: a probe of four subjects returned
13 episodes and missed a widely reported earlier engagement for one of them and
an eight-year relationship for another. So these records are CANDIDATES. Every
one enters review before it can affect a published number.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace

from packages.ids.keys import pair_key, stable_id
from packages.temporal.dates import Censoring, Interval, PreciseDate, from_wikidata

__all__ = ["RelationshipCandidate", "fetch_relationships", "fetch_birth_dates",
           "fetch_gender", "fetch_labels", "SPARQL",
           "LOOKUP_FAILURES", "LABEL_SOURCES"]

SPARQL = "https://query.wikidata.org/sparql"
#: Imported, not copied. See packages/wiki/fetch.py.
from packages.wiki.fetch import USER_AGENT  # noqa: E402,F401
#: Wikidata asks for polite pacing and will 429. Commons returned 429 after
#: about twenty sequential calls during the feasibility probe.
PACE_SECONDS = 1.2


#: Batches whose lookup failed outright, so "still a bare Q-id" can be told
#: apart from "this entity has no English label". Module-level rather than a
#: return value because the single caller wants the labels, and an ambiguity
#: nobody can see is worse than a global nobody reads.
LOOKUP_FAILURES: list[dict] = []
#: qid -> "label" | "enwiki_sitelink", how each name was actually obtained.
LABEL_SOURCES: dict[str, str] = {}


def fetch_labels(qids: list[str], timeout: int = 45) -> dict[str, str]:
    """English labels via wbgetentities, as a fallback for the label SERVICE.

    Measured 2026-09-14, and the cause was not what it looked like. Two pilot
    partners and ten roster partners came back as bare Q-ids, so their episodes
    were flagged partner_label_unresolved and excluded as defective. It was not a
    SERVICE quirk: Q13909 and Q2023710 have NO English label in Wikidata at all,
    though they carry labels in dozens of other languages.

    They do have English Wikipedia sitelinks, which name them Angelina Jolie and
    Tom Holland. A sitelink title is a sourced name rather than a guess, so it is
    the fallback. A person with neither stays unresolved and their episode stays
    excluded, which is the correct outcome for a partner nobody can name.
    """
    import urllib.error

    out: dict[str, str] = {}
    for i in range(0, len(qids), 50):          # the API caps ids per call
        chunk = qids[i:i + 50]
        url = ("https://www.wikidata.org/w/api.php?"
               + urllib.parse.urlencode({
                   "action": "wbgetentities", "ids": "|".join(chunk),
                   "props": "labels|sitelinks", "sitefilter": "enwiki",
                   "languages": "en", "format": "json"}))
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                blob = json.load(fh)
        except (urllib.error.URLError, TimeoutError) as exc:
            # A failed batch and a batch whose entities genuinely have no
            # English label both end as "still a bare Q-id", and the caller
            # could not tell them apart. That ambiguity already cost an
            # investigation: Q13909 was first diagnosed as a SERVICE failure
            # and turned out to have no English label at all.
            LOOKUP_FAILURES.append({"qids": list(chunk), "error": f"{type(exc).__name__}: {exc}"})
            continue
        for qid, entity in (blob.get("entities") or {}).items():
            label = ((entity.get("labels") or {}).get("en") or {}).get("value")
            source = "label"
            if not label:
                # no English label; the English Wikipedia article title is a
                # sourced name for the same entity
                label = ((entity.get("sitelinks") or {}).get("enwiki") or {}).get("title")
                source = "enwiki_sitelink"
            if label:
                out[qid] = label
                # A name from an article title is different provenance from a
                # name from a label. In a project whose product is
                # traceability, which route supplied a person's name is worth
                # being able to answer.
                LABEL_SOURCES[qid] = source
        time.sleep(PACE_SECONDS)
    return out


def _query(sparql: str, timeout: int = 60) -> list[dict]:
    url = SPARQL + "?" + urllib.parse.urlencode({"query": sparql})
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return json.load(fh)["results"]["bindings"]


def _val(row: dict, key: str) -> str | None:
    return row.get(key, {}).get("value")


@dataclass(frozen=True)
class RelationshipCandidate:
    episode_id: str
    pair_key: str
    subject_qid: str
    partner_qid: str
    partner_label: str
    relation: str                      # "spouse" | "unmarried_partner"
    start: PreciseDate | None
    end: PreciseDate | None
    has_reference: bool
    review_status: str = "pending"

    def interval(self, as_of: PreciseDate) -> Interval | None:
        if self.start is None:
            return None
        if self.end is not None:
            return Interval(self.start, self.end, Censoring.CLOSED)
        # No supported end date. An ongoing episode closes at the last supported
        # active date -- never at the run date and never at today.
        return Interval(self.start, None, Censoring.ONGOING, last_supported_active=as_of)

    def as_dict(self) -> dict:
        return {
            "episode_id": self.episode_id, "pair_key": self.pair_key,
            "subject_qid": self.subject_qid, "partner_qid": self.partner_qid,
            "partner_label": self.partner_label, "relation": self.relation,
            "start": None if not self.start else
                {"value": self.start.value, "precision": self.start.precision.value},
            "end": None if not self.end else
                {"value": self.end.value, "precision": self.end.precision.value},
            "has_reference": self.has_reference,
            "review_status": self.review_status,
        }


_REL_QUERY = """
SELECT ?p ?rel ?partner ?partnerLabel ?start ?sPrec ?end ?ePrec ?ref WHERE {
  VALUES ?p { %s }
  { ?p p:P26 ?st . ?st ps:P26 ?partner . BIND("spouse" AS ?rel) }
  UNION
  { ?p p:P451 ?st . ?st ps:P451 ?partner . BIND("unmarried_partner" AS ?rel) }
  OPTIONAL { ?st pq:P580 ?start . ?st pqv:P580 [ wikibase:timePrecision ?sPrec ] }
  OPTIONAL { ?st pq:P582 ?end   . ?st pqv:P582 [ wikibase:timePrecision ?ePrec ] }
  OPTIONAL { ?st prov:wasDerivedFrom ?ref }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def fetch_relationships(qids: list[str]) -> list[RelationshipCandidate]:
    """One batched query, so the endpoint is hit once rather than per person."""
    values = " ".join(f"wd:{q}" for q in qids)
    rows = _query(_REL_QUERY % values)
    time.sleep(PACE_SECONDS)

    seen: dict[tuple, RelationshipCandidate] = {}
    for row in rows:
        subject = (_val(row, "p") or "").rsplit("/", 1)[-1]
        partner = (_val(row, "partner") or "").rsplit("/", 1)[-1]
        relation = _val(row, "rel") or ""
        if not subject or not partner:
            continue
        src = f"wikidata:{subject}:{relation}:{partner}"
        start = end = None
        if _val(row, "start") and _val(row, "sPrec"):
            try:
                start = from_wikidata(_val(row, "start"), int(_val(row, "sPrec")), src)
            except ValueError:
                start = None   # coarser than a year: refused, not widened
        if _val(row, "end") and _val(row, "ePrec"):
            try:
                end = from_wikidata(_val(row, "end"), int(_val(row, "ePrec")), src)
            except ValueError:
                end = None
        key = (subject, partner, relation)
        cand = RelationshipCandidate(
            episode_id=stable_id("rle", subject, partner, relation),
            pair_key=pair_key(subject, partner),
            subject_qid=subject, partner_qid=partner,
            partner_label=_val(row, "partnerLabel") or partner,
            relation=relation, start=start, end=end,
            has_reference=bool(_val(row, "ref")),
        )
        # several reference rows collapse to one candidate; keep the richest
        prior = seen.get(key)
        if prior is None or (cand.start and not prior.start) or (cand.end and not prior.end):
            seen[key] = cand
        elif cand.has_reference and not prior.has_reference:
            seen[key] = cand
    # The label SERVICE sometimes returns a bare Q-id. Look those up directly
    # rather than excluding a real record over one endpoint's quirk.
    unlabelled = sorted({c.partner_qid for c in seen.values()
                         if c.partner_label == c.partner_qid})
    if unlabelled:
        labels = fetch_labels(unlabelled)
        if labels:
            seen = {k: (c if c.partner_qid not in labels
                        else replace(c, partner_label=labels[c.partner_qid]))
                    for k, c in seen.items()}
    return sorted(seen.values(), key=lambda c: (c.subject_qid, c.partner_label))


_GENDER_QUERY = """
SELECT ?p ?genderLabel WHERE {
  VALUES ?p { %s }
  ?p wdt:P21 ?gender .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def fetch_gender(qids: list[str]) -> dict[str, str]:
    """Sourced public-identity gender from Wikidata P21.

    The plan is explicit that this is a SOURCED field. It is never inferred from
    appearance and never from who somebody dated, and a person Wikidata does not
    record is left out of the map rather than guessed at, because an absent
    value is unknown and not a default.
    """
    rows = _query(_GENDER_QUERY % " ".join(f"wd:{q}" for q in qids))
    time.sleep(PACE_SECONDS)
    out: dict[str, str] = {}
    for row in rows:
        qid = (_val(row, "p") or "").rsplit("/", 1)[-1]
        label = (_val(row, "genderLabel") or "").strip().lower()
        if qid and label and not label.startswith("q"):
            out[qid] = label
    return out


_BIRTH_QUERY = """
SELECT ?p ?dob ?prec WHERE {
  VALUES ?p { %s }
  ?p p:P569 ?st . ?st ps:P569 ?dob .
  ?st psv:P569 [ wikibase:timePrecision ?prec ] .
}
"""


def fetch_birth_dates(qids: list[str]) -> dict[str, PreciseDate]:
    """Birth dates with precision, for the adult-window clip."""
    rows = _query(_BIRTH_QUERY % " ".join(f"wd:{q}" for q in qids))
    time.sleep(PACE_SECONDS)
    out: dict[str, PreciseDate] = {}
    for row in rows:
        qid = (_val(row, "p") or "").rsplit("/", 1)[-1]
        try:
            out[qid] = from_wikidata(
                _val(row, "dob"), int(_val(row, "prec")), f"wikidata:{qid}:P569"
            )
        except (ValueError, TypeError):
            continue
    return out
