#!/usr/bin/env python3
"""Put Wikipedia's own words about each relationship beside Wikidata's dates.

Every relationship in this project comes from Wikidata, and the review sheet
asks a person to confirm it. Until now the sheet gave them two Wikidata links
and left the looking-up to them. Nothing cross-checked Wikidata against any
other source, so a wrong date there was a wrong date here.

This reads the English Wikipedia articles for BOTH people and pulls the
sentences that name the other one. Those sentences are the corroboration, and
they are also an independent check: Wikidata statements and article prose are
edited by different people at different times, so agreement is worth something
and disagreement is worth a look.

WHAT THIS IS NOT. It does not decide anything, and a `years_differ` verdict is
NOT a finding that the date is wrong. A sentence naming a partner routinely
carries other years -- a film release, a later event -- and this has no way to
tell which year belongs to which clause. The plan keeps full human review of
real-life factual claims. This reduces the looking-up, never the judging.

Hits the network. Spends no model quota.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402

USER_AGENT = (
    "celeb-couple-M0/0.1 (https://github.com/tonygwu/celeb-couple; read-only research)"
)
#: Sentences longer than this are almost always a list or an infobox dump, and
#: quoting one in a review sheet costs the reader more than it tells them.
MAX_SENTENCE = 320
#: How many excerpts to carry per episode. Two is enough to show agreement or
#: disagreement; more turns the sheet back into homework.
MAX_EXCERPTS = 2


def article_text(title: str, cache: dict[str, str], timeout: int = 60) -> str:
    if title in cache:
        return cache[title]
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "prop": "extracts", "explaintext": "1",
        "format": "json", "redirects": "1", "titles": title})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        pages = json.load(fh)["query"]["pages"]
    text = next(iter(pages.values())).get("extract") or ""
    cache[title] = text
    time.sleep(0.2)
    return text


def sentences_naming(text: str, name: str) -> tuple[list[str], str]:
    """Sentences that name ``name``, and which form matched.

    The full name is tried first. A surname-only match is reported AS a
    surname-only match, because "Hudson" in Kate Hudson's article may be Goldie
    Hawn's son, and a reader who is told which one matched can weigh it.
    Guessing silently between the two is what would make this untrustworthy.
    """
    parts = re.split(r"(?<=[.!?])\s+", text)
    hits = [s.strip() for s in parts if name in s]
    if hits:
        return hits, "full name"
    surname = name.split()[-1]
    if len(surname) < 4:
        return [], "none"
    hits = [s.strip() for s in parts if re.search(rf"\b{re.escape(surname)}\b", s)]
    return hits, "surname only" if hits else "none"


def years_in(sentences: list[str]) -> set[int]:
    out: set[int] = set()
    for s in sentences:
        out.update(int(y) for y in re.findall(r"\b(19\d{2}|20\d{2})\b", s))
    return out


def stored_years(ep: dict) -> set[int]:
    out = set()
    for key in ("start", "end"):
        d = ep.get(key)
        if d and d.get("value"):
            out.add(int(str(d["value"])[:4]))
    return out


def classify(hits: list[str], ep: dict) -> str:
    """A label for the reader, never a verdict.

    The labels are deliberately not verdicts, and they were renamed once for
    that reason. `years_differ` read as a finding; all four episodes it
    selected turned out to be correct dates in sentences that merely carried
    another year, such as "Ford began dating Calista Flockhart after they met
    at the 2002 Golden Globe Awards" beside a stored 2010 marriage. A label a
    reader mistakes for a result is worse than no label.
    """
    if not hits:
        return "not_mentioned"
    found = years_in(hits)
    if not found:
        return "mentioned_no_year"
    want = stored_years(ep)
    if not want:
        return "no_stored_date"
    return ("prose_confirms_a_stored_year" if found & want
            else "prose_names_other_years")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=("Pull Wikipedia's own sentences about each relationship "
                     "so the review sheet shows evidence, not just links. "
                     "Hits the network; spends no quota."))
    ap.add_argument("--episodes", default="data/pilot/records/episodes.json")
    ap.add_argument("--out", default="data/pilot/records/relationship_corroboration.json")
    args = ap.parse_args()

    episodes = require(REPO, args.episodes)
    cache: dict[str, str] = {}
    rows = []

    for ep in episodes["episodes"]:
        subject, partner = ep["subject_name"], ep["partner_label"]
        excerpts, matched, sides = [], set(), []
        # Both articles, because either editor may have written the date and
        # a one-sided check would report "not mentioned" for a relationship
        # the other article documents fully.
        for reader, about in ((subject, partner), (partner, subject)):
            try:
                text = article_text(reader, cache)
            except Exception as exc:                       # noqa: BLE001
                sides.append({"article": reader, "error": f"{type(exc).__name__}"})
                continue
            hits, how = sentences_naming(text, about)
            hits = [h for h in hits if len(h) <= MAX_SENTENCE]
            sides.append({"article": reader, "matched_on": how,
                          "sentences_found": len(hits)})
            for h in hits[:MAX_EXCERPTS]:
                excerpts.append({"from_article": reader, "matched_on": how,
                                 "text": h})
            matched.update(hits)

        verdict = classify(sorted(matched), ep)
        rows.append({
            "episode_id": ep["episode_id"], "subject": subject,
            "partner": partner, "verdict": verdict,
            "stored_years": sorted(stored_years(ep)),
            "years_in_prose": sorted(years_in(sorted(matched))),
            "sides": sides,
            "excerpts": excerpts[:MAX_EXCERPTS * 2],
        })

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    payload = {
        "episodes_checked": len(rows),
        "verdict_counts": counts,
        "rows": rows,
        "note": ("Corroboration for a human reader, NOT a verification. "
                 "`prose_names_other_years` means the prose named no year "
                 "this project stored. On the first run all four such "
                 "episodes had CORRECT dates, in sentences that carried "
                 "another year for another reason. It is a sort order for a "
                 "reader's attention, not a finding. Wikidata statements and "
                 "article prose are edited by different people, which is what "
                 "makes agreement worth anything."),
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")

    for r in sorted(rows, key=lambda r: r["verdict"]):
        print(f"  {r['verdict']:18} {r['subject'][:20]:20} + {r['partner'][:22]:22} "
              f"stored={r['stored_years']} prose={r['years_in_prose'][:6]}")
    print(f"\n{len(rows)} episodes: " +
          ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
