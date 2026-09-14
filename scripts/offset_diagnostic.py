#!/usr/bin/env python3
"""Cross-gender offset sensitivity, run against the real scored board.

The plan discloses that one rubric applied to both genders makes equal scores a
MODELLING CONVENTION rather than a measured equivalence. A disclosure alone
does not show how much the board depends on that convention, so this measures
it: shift every partner-side estimate by a constant delta and report what moves.

The identity the diagnostic tests against itself:

    dPAW_total(p) = delta * scored_exposure(p)   , mirrored sign in the other view
    dPAW_rate(p)  = delta                        , identical for everyone in a view

which predicts that a constant offset CANNOT reorder PAW rate inside a view,
while it can reorder cumulative PAW because exposure differs per person. If
rate ranks ever move here, the implementation is wrong.

Spends no model quota.
"""
from __future__ import annotations
import argparse, json, sys
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from modules.analytics.metrics import (                              # noqa: E402
    Pairing, PeriodExposure, apply_cross_gender_offset, as_estimate,
    paw_rate, paw_total, scored_exposure,
)

DELTAS = [Fraction(d) for d in (-6, -4, -2, 0, 2, 4, 6)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="data/pilot/run/evidenced_scores.json")
    ap.add_argument("--out", default="data/pilot/run/offset_diagnostic.json")
    args = ap.parse_args()

    blob = json.loads((REPO / args.scores).read_text())
    pairings = blob.get("scored_pairings", [])
    if not pairings:
        print("no scored pairings; nothing to diagnose")
        return 0

    by_focal: dict[str, list[Pairing]] = {}
    for p in pairings:
        if p.get("gap_mens_view") is None:
            continue
        k = Pairing(
            p["pairing_id"] if "pairing_id" in p else f"{p['domain']}_{p['period']}",
            p["focal_male"], p["female"], p["domain"],
            (PeriodExposure(p["period"], Fraction(1),
                            as_estimate(p["male_estimate"]),
                            as_estimate(p["female_estimate"]),
                            f"se_m_{p['male_estimate_from']}",
                            f"se_f_{p['female_estimate_from']}"),),
        )
        by_focal.setdefault(p["focal_male"], []).append(k)

    if not by_focal:
        print("no scorable pairings")
        return 0

    rows = []
    for delta in DELTAS:
        totals, rates = {}, {}
        for person, ks in by_focal.items():
            shifted = [apply_cross_gender_offset(k, delta) for k in ks]
            totals[person] = float(paw_total(shifted))
            r = paw_rate(shifted)
            rates[person] = None if r is None else float(r)
        order = lambda d: [n for n, _ in sorted(
            d.items(), key=lambda kv: (-(kv[1] if kv[1] is not None else -1e9), kv[0]))]
        rows.append({"delta": float(delta),
                     "paw_total": totals, "paw_rate": rates,
                     "total_order": order(totals), "rate_order": order(rates)})

    base = next(r for r in rows if r["delta"] == 0.0)
    identity_ok, rate_order_stable = True, True
    for r in rows:
        for person, ks in by_focal.items():
            expected_total = base["paw_total"][person] + r["delta"] * float(
                scored_exposure(ks))
            if abs(r["paw_total"][person] - expected_total) > 1e-9:
                identity_ok = False
            if base["paw_rate"][person] is not None:
                expected_rate = base["paw_rate"][person] + r["delta"]
                if abs(r["paw_rate"][person] - expected_rate) > 1e-9:
                    identity_ok = False
        if r["rate_order"] != base["rate_order"]:
            rate_order_stable = False

    total_order_changed = any(r["total_order"] != base["total_order"] for r in rows)
    report = {
        "deltas": [float(d) for d in DELTAS],
        "people": sorted(by_focal),
        "identity_holds": identity_ok,
        "rate_ranks_stable_under_constant_offset": rate_order_stable,
        "cumulative_ranks_changed": total_order_changed,
        "reading": (
            "A constant cross-gender offset shifts every PAW rate by exactly "
            "delta, so rate ranks inside a view cannot move. Cumulative PAW is "
            "exposure-weighted, so it can. "
            + ("Cumulative ranks did move over the tested range."
               if total_order_changed else
               "Cumulative ranks did NOT move over the tested range, which with "
               "this few people and this little exposure spread says the board is "
               "too small to be sensitive rather than that it is robust.")
        ),
        "caveat": (
            "This is a sensitivity scenario, not an estimate of real-world bias. "
            "Genders are never silently recentred."
        ),
        "rows": rows,
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}, indent=2))
    print(f"wrote {out}")
    return 0 if identity_ok and rate_order_stable else 1


if __name__ == "__main__":
    raise SystemExit(main())
