#!/usr/bin/env python3
"""Resolve a list of display names to Wikidata ids, producing a roster file.

The 100-name roster was resolved by an inline snippet, which meant the roster
could not be rebuilt or extended by anyone else. Names come in on stdin or from
a file, one per line, with a `# men` / `# women` marker setting the gender for
the lines that follow.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, sys, time, urllib.parse, urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
UA = ("celeb-couple-M1/0.1 (https://github.com/tonygwu/celeb-couple; "
      "read-only research)")
#: Descriptions that mark the right kind of entity when a name is ambiguous.
PREFER = ("actor", "actress", "comedian", "singer", "film", "model")


def resolve(name: str, timeout: int = 30):
    url = ("https://www.wikidata.org/w/api.php?"
           + urllib.parse.urlencode({
               "action": "wbsearchentities", "format": "json", "language": "en",
               "type": "item", "limit": "5", "search": name}))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        hits = json.load(fh).get("search", [])
    best = next((h for h in hits
                 if any(k in (h.get("description") or "").lower() for k in PREFER)),
                hits[0] if hits else None)
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", help="file of names; '# men' / '# women' set gender")
    ap.add_argument("--version", required=True)
    ap.add_argument("--basis", required=True,
                    help="how the roster was chosen; recorded in the file")
    ap.add_argument("--pace", type=float, default=0.35)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    text = (Path(args.names).read_text() if args.names else sys.stdin.read())
    gender, people, unresolved = "unknown", [], []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            token = line.lstrip("#").strip().lower()
            if token in ("men", "male"):
                gender = "male"
            elif token in ("women", "female"):
                gender = "female"
            continue
        hit = resolve(line)
        if hit is None:
            unresolved.append(line)
        people.append({"display_name": line,
                       "wikidata_qid": hit["id"] if hit else None,
                       "gender_category": gender,
                       "cohort_note": "roster",
                       "description": hit.get("description") if hit else None})
        time.sleep(args.pace)

    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"version": args.version,
                               "selected_on": args.version.split("-", 1)[-1],
                               "selection_basis": args.basis,
                               "people": people}, indent=2))
    print(f"resolved {sum(1 for p in people if p['wikidata_qid'])}/{len(people)}")
    if unresolved:
        print(f"UNRESOLVED (left with a null id, not guessed): {unresolved}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
