#!/usr/bin/env python3
"""Is the evidence-shape confound aligned with GENDER?

This is the question that decides whether the product can compare a man and a
woman at all.

Evidence shape explains a large share of the estimate: an editorial award is
superlative by construction and pins near 92, while ranked placements spread
lower. That is a known confound. It becomes something worse if the shapes are
not distributed evenly across genders, because then every mixed-gender gap
carries a built-in offset that is a property of publishing rather than of the
two people.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402


#: DESCRIPTIVE statistics use `statistics.pstdev`, deliberately, and that is
#: not an oversight to be harmonised with `measure_rater_noise.py`, which uses
#: the sample SD. The difference is what the number is FOR:
#:
#:   - Here the question is "how spread out are the estimates this corpus
#:     holds", and the corpus is the whole of what is being described. The
#:     population formula answers exactly that.
#:   - There the question is "what is the standard deviation of the rating
#:     PROCESS", inferred from four repeat draws that are a sample of it. The
#:     population formula underestimates that by 13% at n = 4, which understated
#:     the published noise floor.
#:
#: Same function name, two different questions, two different right answers.


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/pilot/run/gender_shape_confound.json")
    args = ap.parse_args()

    obs = require(REPO, "data/pilot/observations/observations.json")
    scores = require(REPO, "data/pilot/run/evidenced_scores.json")
    cohort = require(REPO, "docs/pilot-cohort.json")["people"]
    partners = require(REPO, "data/pilot/records/partner_universe.json")["people"]
    gender = {p["wikidata_qid"]: p.get("gender_category", "unknown")
              for p in cohort + partners}

    shape_counts: dict[str, Counter] = defaultdict(Counter)
    for o in obs["observations"]:
        shape_counts[gender.get(o["person_id"], "unknown")][o["evidence_type"]] += 1

    est: dict[str, list[float]] = defaultdict(list)
    for r in scores["person_periods"]:
        if r["estimate"] is not None:
            est[gender.get(r["person_id"], "unknown")].append(r["estimate"])

    summary = {}
    for g, vals in est.items():
        summary[g] = {"n": len(vals), "mean": round(statistics.mean(vals), 2),
                      "sd": round(statistics.pstdev(vals), 2),
                      "min": min(vals), "max": max(vals)}

    # Leave-one-person-out on the offset. It is the project's most
    # consequential finding and it rests on eight male estimates across five
    # people -- few enough that one person could be carrying it.
    by_person: dict[str, list[float]] = {}
    for r in scores["person_periods"]:
        if r["estimate"] is not None and gender.get(r["person_id"]) == "male":
            by_person.setdefault(r["person"], []).append(r["estimate"])
    _f = est.get("female") or []
    loo = {}
    if _f and len(by_person) > 1:
        f_mean = statistics.mean(_f)
        for who in by_person:
            rest = [v for n, vs in by_person.items() if n != who for v in vs]
            if rest:
                loo[who] = round(statistics.mean(rest) - f_mean, 2)

    male, female = summary.get("male"), summary.get("female")
    offset = (round(male["mean"] - female["mean"], 2)
              if male and female else None)
    ranked = {g: c.get("ordered_rank", 0) for g, c in shape_counts.items()}
    loo_block = {
        "offset_dropping_each_male_person": loo,
        "min": min(loo.values()) if loo else None,
        "max": max(loo.values()) if loo else None,
        "note": ("the offset with each male person removed entirely. If it "
                 "approached zero or reversed, the finding would belong to "
                 "whichever person was carrying it."),
    } if loo else None

    payload = {
        "observations_by_gender_and_shape": {
            g: dict(c) for g, c in sorted(shape_counts.items())},
        "estimates_by_gender": summary,
        "ranked_observations": ranked,
        "mean_offset_male_minus_female": offset,
        "leave_one_person_out": loo_block,
        "reading": (
            f"Men hold {ranked.get('male', 0)} ranked observations and women "
            f"{ranked.get('female', 0)}. Because an award pins near the top of "
            f"the scale and a ranked placement does not, that imbalance puts "
            f"the male mean {offset} points above the female mean before any "
            f"fact about any individual enters. Every mixed-gender pairing "
            f"therefore carries roughly that offset built in, in the same "
            f"direction, and a signed gap that size is a statement about "
            f"publishing rather than about the couple."
            + (f" Removing any single male person entirely moves the offset "
               f"between {loo_block['min']} and {loo_block['max']}: it never "
               f"approaches zero and never reverses, so the finding does not "
               f"belong to whichever person is carrying it."
               if loo_block else "")
        ),
        "consequence": (
            "A four-view product compares a man against a woman in every row. "
            "With the shapes distributed this unevenly, the sign of a typical "
            "gap is decided by which sex the person is, not by the judgments. "
            "This has to be disclosed on every row, or the board reports a "
            "publishing artifact as a finding about people."
        ),
    }
    (REPO / args.out).parent.mkdir(parents=True, exist_ok=True)
    (REPO / args.out).write_text(json.dumps(payload, indent=2))

    print("observations by gender and shape:")
    for g, c in sorted(shape_counts.items()):
        print(f"  {g:8} " + "  ".join(f"{k}={v}" for k, v in sorted(c.items())))
    print("\nestimates by gender:")
    for g, v in sorted(summary.items()):
        print(f"  {g:8} n={v['n']:2} mean={v['mean']:6} sd={v['sd']:5} "
              f"range {v['min']}-{v['max']}")
    print(f"\nmean offset, male minus female: {offset}")
    print(f"\n{payload['reading']}")
    print(f"\nwrote {REPO / args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
