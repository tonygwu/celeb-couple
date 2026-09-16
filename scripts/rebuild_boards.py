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
from modules.pairing import merge as mg                    # noqa: E402

SEX = {"male": "male", "female": "female"}


def volume_confound(rows: list[dict]) -> float | None:
    """How much of the cumulative board is just a count of romances.

    Carried over from build_boards.py because it earned its place there: on the
    film-anchored data it showed 90% of the women's on-screen cumulative ranking
    was explained by romance COUNT rather than by partner. A board that is
    really a counter should say so where it is read.
    """
    if len(rows) < 3:
        return None
    xs = [r["exposure"] for r in rows]
    ys = [r["paw_total"] for r in rows]
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return (sxy * sxy) / (sxx * syy)


CANON_FAMILY = "canonical"


def population_from_gradings(canon: dict, sex_of: dict) -> dict:
    """(CANON_FAMILY, sex, person, period) -> the canonical mean score.

    One synthetic family, because a canonical score has no family: it is the
    mean of every grading of that person-year, whichever model produced it.
    Using the same key shape lets normalize_population z-score within sex with
    no change to it.
    """
    pop = {}
    for key, v in canon.items():
        qid, period = key.split("|", 1)
        sex = sex_of.get(qid)
        if sex is None:
            continue
        pop[(CANON_FAMILY, sex, qid, str(period))] = Fraction(str(v["score"]))
    return pop


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
    ap.add_argument("--graph", action="append", default=None,
                    help="repeatable. The IMDb graph is on-screen ONLY, so the "
                         "real-life boards stay empty unless the Wikidata "
                         "relationship graph is passed too.")
    ap.add_argument("--min-year", type=int, default=1990,
                    help="scope floor, applied AFTER the merge so it covers every "
                         "source. Reported, never silent.")
    ap.add_argument("--families", default="fable,astra")
    ap.add_argument("--gradings", default="data/roster100/run/person_gradings.json",
                    help="canonical scores from build_person_gradings.py")
    ap.add_argument("--per-family", action="store_true",
                    help="score each judge family separately, the pre-2026-09-16 "
                         "behaviour. Default is the canonical mean of every grading.")
    ap.add_argument("--out", default=None, help="HTML destination")
    ap.add_argument("--template", default=str(REPO / "web/board.html"))
    args = ap.parse_args()

    cache = caches(args.cache or ["data/roster100/run/person_period_cache.json",
                                  "data/roster100/run/person_period_cache_astra.json"])
    sources = args.graph or ["data/roster100/run/pairing_scores.json"]
    loaded = []
    for rel in sources:
        if not (REPO / rel).exists():
            print(f"  (no {rel}; skipping)")
            continue
        loaded.append((rel, require(REPO, rel)["pairings"]))
    # Semantic identity, NOT pairing_id: the IMDb graph names a film by tconst
    # and the Wikidata graph names the same film by QID, so the two ids differ
    # for one romance. See modules/pairing/merge.py.
    merged, mstats = mg.merge_graphs(loaded)
    before = len(merged)
    merged = [p for p in merged
              if str(p.get("period") or "").isdigit() and int(p["period"]) >= args.min_year]
    graph = {"pairings": merged}
    if before != len(merged):
        print(f"  scope floor {args.min_year}: dropped {before - len(merged):,} "
              f"pairings before it")
    for rel, rows in loaded:
        print(f"  {rel}: {len(rows):,} pairings, {mstats['by_source'][rel]:,} kept")
    print(f"  merged {mstats['seen']:,} -> {len(merged):,}  "
          f"(duplicates dropped {mstats['duplicates_dropped']:,}, "
          f"unidentifiable kept {mstats['without_both_qids']:,})")
    for ex in mstats["dropped_examples"][:3]:
        print(f"    dup: {ex['who']} in {ex['work']!r} ({ex['period']}) "
              f"kept from {ex['kept_from']}")

    # sex is not stored per cache entry; the pairing graph knows it
    sex_of = {}
    for p in graph["pairings"]:
        if p.get("male_qid"): sex_of[p["male_qid"]] = "male"
        if p.get("female_qid"): sex_of[p["female_qid"]] = "female"
    for e in cache.values():
        e["sex"] = sex_of.get(e["person_id"], "male")

    if args.per_family:
        pop = population_from_cache(cache)
        fams = [f.strip() for f in args.families.split(",") if f.strip()]
        spread_of = {}
    else:
        blob = require(REPO, args.gradings)
        canon = blob["canonical"]
        pop = population_from_gradings(canon, sex_of)
        fams = [CANON_FAMILY]
        # The per-tuple disagreement the mean hides. Shown on the board rather
        # than dropped, because a row built on one grading and a row built on
        # five are not equally certain.
        spread_of = {(k.split("|", 1)[0], k.split("|", 1)[1]): v["spread"]
                     for k, v in canon.items()}
        print(f"canonical person-years {len(canon):,}  "
              f"placed on the board population {len(pop):,}")
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
                     "spread": max(
                         [s for s in (spread_of.get((p.get("male_qid"), per)),
                                      spread_of.get((p.get("female_qid"), per)))
                          if s is not None] or [None], default=None),
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
                    "min_year": args.min_year,
                    "norm_method": ("z-score within sex over CANONICAL scores, film-blind"
                                    if not args.per_family else
                                    "z-score within (judge family, sex), film-blind")},
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
            # Each row carries the person's OWN score over time, so the board
            # can draw a trajectory. Every chart shares one x-axis range, set
            # below from the whole population, or the rows would not be
            # comparable to each other.
            for row in rows:
                ser = {}
                for (f, s, qq, per), v in pop.items():
                    if qq != row["qid"]:
                        continue
                    # The trajectory obeys the same scope floor as the board.
                    # Without this a person scored in 1978 for a pairing the
                    # floor removed still stretched the shared x-axis to 1978.
                    if int(per) < args.min_year:
                        continue
                    nv = norm.get((f, s, qq, per))
                    ser.setdefault(int(per), []).append((float(v), float(nv) if nv is not None else None))
                row["series"] = [
                    {"y": y,
                     "raw": round(st.mean([a for a, _ in vs]), 3),
                     "n": (round(st.mean([b for _, b in vs if b is not None]), 3)
                           if any(b is not None for _, b in vs) else None)}
                    for y, vs in sorted(ser.items())]
            out["boards"].append({"gender": gender, "domain": dom, "label": f"{gl} — {dl}",
                                  "r2": volume_confound(rows), "rows": rows})
            print(f"  {gl} — {dl}: {len(rows)} ranked")

    years = sorted({int(p) for (_f, _s, _q, p) in pop if int(p) >= args.min_year})
    out["meta"]["year_min"] = years[0] if years else None
    out["meta"]["year_max"] = years[-1] if years else None
    out["meta"]["people_ranked"] = len({r["qid"] for b in out["boards"] for r in b["rows"]})
    # Honesty on the page: most scores carry NO published evidence, and the
    # page must not imply the rankings drive them.
    canon_all = (require(REPO, args.gradings)["canonical"] if not args.per_family else {})
    out["meta"]["person_years"] = len(canon_all)
    out["meta"]["with_evidence"] = sum(1 for v in canon_all.values() if v["any_evidence"])
    out["meta"]["works"] = len({r["work"] for r in recs if r.get("work")})

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
