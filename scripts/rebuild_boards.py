#!/usr/bin/env python3
"""Everything downstream of the cache, in one command. Read-only, spends nothing.

Cache -> pairing gaps -> within-sex normalization -> four boards -> one HTML file.

The cache is the only thing that costs money. Everything here is arithmetic over
it, so re-running after grading 200 more person-years is free.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.artifacts import require               # noqa: E402
from packages.llmkit.contract import PERSON_RUBRIC_VERSION  # noqa: E402
from modules.pairing import normalize as nz                 # noqa: E402
from modules.pairing.boards import build_board              # noqa: E402
from modules.pairing.person import cache_key                # noqa: E402

SEX = {"male": "male", "female": "female"}


def caches(paths: list[str]) -> dict:
    out: dict = {}
    for p in paths:
        f = REPO / p
        if f.exists():
            out.update(json.loads(f.read_text()))
    return out


def population_from_cache(cache: dict) -> dict:
    """(family, sex, person, period) -> score, straight from the cache.

    The cache IS the population plan v4 §4a asks for: one judged score per
    person-year per family. No verdict re-reading, no film context to strip.
    """
    pop = {}
    for e in cache.values():
        if not e.get("judged") or e.get("score") is None:
            continue
        pop[(e["family"], e["sex"], e["person_id"], str(e["period"]))] = \
            Fraction(str(e["score"]))
    return pop


def main() -> int:
    ap = argparse.ArgumentParser(description="Rebuild the boards from the cache. Free.")
    ap.add_argument("--cache", action="append", default=None)
    ap.add_argument("--graph", default="data/roster100/run/pairing_scores.json")
    ap.add_argument("--families", default="fable,astra")
    ap.add_argument("--out", default=None, help="HTML destination")
    ap.add_argument("--template",
                    default="/private/tmp/claude-501/-Users-tonygwu-Code-misc-celebrity-couple/"
                            "cad88ae2-bc88-4d63-8771-172c642cc167/scratchpad/page.html")
    args = ap.parse_args()

    cache = caches(args.cache or ["data/roster100/run/person_period_cache.json",
                                  "data/roster100/run/person_period_cache_astra.json"])
    graph = require(REPO, args.graph)
    fams = [f.strip() for f in args.families.split(",") if f.strip()]

    # sex is not stored per cache entry; the pairing graph knows it
    sex_of = {}
    for p in graph["pairings"]:
        if p.get("male_qid"): sex_of[p["male_qid"]] = "male"
        if p.get("female_qid"): sex_of[p["female_qid"]] = "female"
    for e in cache.values():
        e["sex"] = sex_of.get(e["person_id"], "male")

    pop = population_from_cache(cache)
    norm = nz.normalize_population(pop)
    print(f"cache entries {len(cache)}  judged {len(pop)}  normalized {len(norm)}")

    def look(qid, per, fam, table):
        return table.get((fam, sex_of.get(qid, "male"), qid, str(per)))

    recs, names = [], {}
    for p in graph["pairings"]:
        per = str(p.get("period") or "")
        raw_f, nrm_f, absol, nabs = {}, {}, {}, {}
        for fam in fams:
            m, w = look(p.get("male_qid"), per, fam, pop), look(p.get("female_qid"), per, fam, pop)
            if m is None or w is None:
                continue
            raw_f[fam] = float(w - m)
            nm, nw = look(p.get("male_qid"), per, fam, norm), look(p.get("female_qid"), per, fam, norm)
            if nm is not None and nw is not None:
                nrm_f[fam] = float(nw - nm)
            absol.setdefault("m", []).append(float(m)); absol.setdefault("f", []).append(float(w))
            if nm is not None:
                nabs.setdefault("m", []).append(float(nm)); nabs.setdefault("f", []).append(float(nw))
        if p.get("male_qid"): names[p["male_qid"]] = p.get("male") or p["male_qid"]
        if p.get("female_qid"): names[p["female_qid"]] = p.get("female") or p["female_qid"]
        recs.append({**{k: p.get(k) for k in ("pairing_id","domain","period","work",
                                              "male","female","male_qid","female_qid")},
                     "gap": (sum(raw_f.values())/len(raw_f)) if raw_f else None,
                     "n_gap_raw": (sum(nrm_f.values())/len(nrm_f)) if nrm_f else None,
                     "judges": raw_f,
                     # binary: a romance counts fully, a non-romance not at all
                     "centrality": (1.0 if (p.get("centrality") or 0) > 0 else 0.0)
                                   if p.get("centrality") is not None else None,
                     "abs": {k: st.mean(v) for k, v in absol.items()},
                     "nabs": {k: st.mean(v) for k, v in nabs.items()}})

    covered = sum(1 for r in recs if r["gap"] is not None)
    gaps = [r["gap"] for r in recs if r["gap"] is not None and (r.get("centrality") or 0) > 0]
    spreads = [max(r["judges"].values()) - min(r["judges"].values())
               for r in recs if len(r.get("judges") or {}) > 1]
    floor = st.mean(spreads) if spreads else 0.28
    print(f"pairings {len(recs)}  with a gap {covered}  scoring {len(gaps)}  floor {floor:.3f}")

    nrecs = [{**r, "gap": r["n_gap_raw"]} for r in recs]
    out = {"meta": {"floor": floor, "both_judged": len(spreads),
                    "judged": covered, "scoring": len(gaps),
                    "offset": st.mean(gaps) if gaps else 0.0,
                    "contract": (next(iter(cache.values()))["contract"]["contract_id"]
                                 if cache else "?"),
                    "rubric": PERSON_RUBRIC_VERSION,
                    "norm_method": "z-score within (judge family, sex), film-blind"},
           "boards": []}
    for gender, gl in (("male","Men"), ("female","Women")):
        for dom, dl in (("on_screen","On screen"), ("real_life","Real life")):
            male = gender == "male"
            rows = build_board(recs, gender=gender, domain=dom, names=names, min_pairings=2)
            nrows = {r["qid"]: r for r in
                     build_board(nrecs, gender=gender, domain=dom, names=names, min_pairings=2)}
            by = {r["pairing_id"]: r for r in recs}
            for row in rows:
                n = nrows.get(row["qid"])
                row["n_total"], row["n_rate"] = (n["paw_total"], n["paw_rate"]) if n else (None, None)
                ncs = {(c["other"], c["period"], c["work"]): c
                       for c in (n["contributions"] if n else [])}
                for c in row["contributions"]:
                    src = next((x for x in recs
                                if x["period"] == c["period"] and x["work"] == c["work"]
                                and (x["male_qid"] if male else x["female_qid"]) == row["qid"]
                                and (x["female"] if male else x["male"]) == c["other"]), None)
                    if src:
                        a, na = src["abs"], src["nabs"]
                        if a:
                            c["self_abs"] = round(a["m"] if male else a["f"], 2)
                            c["other_abs"] = round(a["f"] if male else a["m"], 2)
                        if na:
                            c["self_n"] = round(na["m"] if male else na["f"], 2)
                            c["other_n"] = round(na["f"] if male else na["m"], 2)
                    k = ncs.get((c["other"], c["period"], c["work"]))
                    if k: c["n_gap"] = round(k["signed_gap"], 2)
            out["boards"].append({"gender": gender, "domain": dom, "label": f"{gl} — {dl}",
                                  "r2": None, "rows": rows})
            print(f"  {gl} — {dl}: {len(rows)} ranked")

    dest = Path(args.out).expanduser() if args.out else Path.home()/"Desktop"/"punching-above-weight.html"
    tpl = Path(args.template).read_text()
    body = tpl.replace("__DATA__", json.dumps(out, separators=(",",":"))) \
        if "__DATA__" in tpl else \
        tpl[:tpl.index("const DATA = ")] + "const DATA = " + \
        json.dumps(out, separators=(",",":")) + ";" + tpl[tpl.index("\n", tpl.index("const DATA = ")):]
    dest.write_text(body)
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
