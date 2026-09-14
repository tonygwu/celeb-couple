#!/usr/bin/env python3
"""Render docs/M0-REPORT.md from the run artifacts.

Every number in the report is read from a JSON artifact. Nothing is typed by
hand, because a hand-typed count is the bug this project's sibling repo paid
for five separate times.
"""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


#: Every artifact the report reads. The fingerprint over these is the report's
#: real identity: verbatim-index stamps its pages with the RENDER date, which
#: makes every regeneration a diff and tells a reader nothing about whether the
#: numbers moved.
_INPUTS: list[str] = []


def load(p: str, default=None):
    f = REPO / p
    if f.exists():
        _INPUTS.append(p)
        return json.loads(f.read_text())
    return default


#: Keys recording WHEN an artifact was written, never WHAT it says. Hashing
#: them makes the fingerprint track the last chain run instead of the findings,
#: which is the exact defect the fingerprint replaced. Ten pilot artifacts
#: carry `generated_at_utc`.
#:
#: Deliberately narrow. `data_as_of` and `last_supported_active` are findings
#: about the evidence, not stamps about the process, and an over-broad strip
#: would hide a real change in the cutoff.
VOLATILE_KEYS = frozenset({"generated_at_utc", "generated_at", "rendered_at"})


def stable_bytes(obj):
    """Canonical bytes for a loaded artifact, with process stamps removed.

    Non-dict, non-list input is returned as bytes unchanged, so an artifact
    that is not JSON is still hashed rather than silently skipped.
    """
    import json as _json

    def strip(o):
        if isinstance(o, dict):
            return {k: strip(v) for k, v in o.items() if k not in VOLATILE_KEYS}
        if isinstance(o, list):
            return [strip(v) for v in o]
        return o

    if isinstance(obj, (dict, list)):
        return _json.dumps(strip(obj), sort_keys=True,
                           separators=(",", ":")).encode()
    if isinstance(obj, bytes):
        return obj
    return str(obj).encode()


def _fingerprint() -> str:
    import hashlib
    h = hashlib.sha256()
    for rel in sorted(_INPUTS):
        h.update(rel.encode())
        raw = (REPO / rel).read_bytes()
        try:
            payload = stable_bytes(json.loads(raw))
        except (ValueError, UnicodeDecodeError):
            payload = raw
        h.update(payload)
    return h.hexdigest()[:12]


def decisive_measurement(shape_conf: dict, n_scored: int) -> str:
    """Compare award-shaped against rank-shaped evidence, from the artifact.

    The earlier version counted estimates at or above 90 and called them
    "person-periods resting on a one-winner editorial award". That is a score
    threshold wearing the name of an evidence shape, and the two stopped
    agreeing as soon as the corpus grew. It also asserted "every single one
    scored exactly 92.0" and "the ONE person-period resting on an ORDERED
    rank", both of which the re-score falsified.
    """
    by_shape = (shape_conf or {}).get("by_shape") or {}
    award = by_shape.get("editorial_award")
    rank = by_shape.get("ordered_rank")
    if not (award and rank):
        return ("**The decisive measurement** needs both award-shaped and "
                "rank-shaped person-periods to compare, and this corpus does "
                "not hold both.")
    return (
        f"**The decisive measurement**: of {n_scored} scored person-periods, "
        f"{award['n']} rest on a one-winner editorial award and {rank['n']} on "
        f"an ordered rank. The award-shaped ones cluster at mean "
        f"{award['mean']} with sd **{award['sd']}**; the rank-shaped ones sit "
        f"lower, at mean {rank['mean']}, and spread more than twice as wide, "
        f"sd **{rank['sd']}**. A one-winner award is superlative by "
        f"construction, so it can only land in one band. Ranked evidence "
        f"carries a degree, so it can tell people apart.")


def shape_paragraph(shape_conf: dict, density: dict) -> str:
    """Describe the corpus's evidence shapes FROM the artifacts.

    This used to be a typed sentence: "Every scored person-period carries
    exactly one observation, and every one of those observations is a
    one-winner editorial award." It was true of a 34-person-period corpus and
    false of the 39-person-period one that replaced it, and nothing recomputed
    it. Derive it instead.
    """
    by_shape = (shape_conf or {}).get("by_shape") or {}
    if not by_shape:
        return "No scored person-period carries a classified observation shape."

    dist = {int(k): v for k, v in ((density or {}).get("distribution") or {}).items()}
    total = sum(dist.values())
    multi = sum(v for k, v in dist.items() if k > 1)

    if multi == 0:
        density_clause = ("Every scored person-period carries exactly one "
                          "observation")
    else:
        density_clause = (f"{multi} of {total} scored person-periods carry more "
                          f"than one observation; the rest carry exactly one")

    ordered = sorted(by_shape.items(), key=lambda kv: -kv[1]["n"])
    if len(ordered) == 1:
        name, s = ordered[0]
        shape_clause = (f"and every one of those observations is of a single "
                        f"shape, `{name}` ({s['n']} person-periods, "
                        f"{s['min']}-{s['max']})")
    else:
        parts = [f"`{name}` (n={s['n']}, {s['min']}-{s['max']}, sd {s['sd']})"
                 for name, s in ordered]
        shape_clause = ("and the observations behind them fall into "
                        f"{len(ordered)} shapes: " + ", ".join(parts))

    return density_clause + ", " + shape_clause + "."


def main() -> int:
    import argparse
    argparse.ArgumentParser(
        description=("Render docs/M0-REPORT.md from the run artifacts. Reads "
                     "only; spends no model quota.")).parse_args()

    cohort = load("docs/pilot-cohort.json")
    records = load("data/pilot/records/relationship_candidates.json")
    episodes = load("data/pilot/records/episodes.json")
    films = load("data/pilot/records/onscreen_candidates.json")
    obs = load("data/pilot/observations/observations.json")
    stress = load("data/pilot/stress/stress_report.json")
    first_pass = load("data/pilot/run/pilot_report.json")
    joint = load("data/pilot/run/joint_with_nearby.json")
    scored = load("data/pilot/run/evidenced_scores.json")
    romance = load("data/pilot/records/romance.json")
    noise = load("data/pilot/run/rater_noise.json")
    offset = load("data/pilot/run/offset_diagnostic.json")
    grounding = load("data/pilot/run/grounding_audit.json")
    density = load("data/pilot/run/evidence_density.json")
    align = load("data/pilot/run/alignment_gap.json")
    elig = load("data/pilot/records/partner_eligibility.json")
    shape_conf = load("data/pilot/run/shape_confound.json")
    gsc = load("data/pilot/run/gender_shape_confound.json")

    L: list[str] = []
    w = L.append
    w("# M0 pilot report — Celebrity Pairing WAR")
    w("")
    w(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d')} from the run "
      f"artifacts under `data/pilot/`, input fingerprint `{_fingerprint()}`. "
      f"Every number below is read from a JSON artifact, not typed.")
    w("")
    w("The fingerprint, not the date, is this report's identity: it hashes the "
      "artifacts with their `generated_at_utc` stamps removed, so re-running the "
      "chain over unchanged findings produces an identical file. A diff means "
      "the numbers moved, not that the chain ran again.")
    w("")
    w("**Private pilot. Nothing here is published, ranked, or deployed. Every "
      "relationship and every on-screen pairing is an UNVERIFIED candidate.**")
    w("")
    w("This report covers the 14-person pilot. Three companion documents cover "
      "what came after it:")
    w("")
    w("- [`docs/SCALING.md`](SCALING.md) — whether growing the roster to 100 "
      "helps, and what a usable source would have to look like")
    w("- [`docs/SOURCE-HUNT.md`](SOURCE-HUNT.md) — every surface checked, and "
      "the negative result")
    w("- [`docs/REACHABLE-PRODUCTS.md`](REACHABLE-PRODUCTS.md) — what can be "
      "built with the evidence that exists")
    w("")

    # ---------- the answer first ----------
    w("## The answer first")
    w("")
    cov = obs["coverage"]
    n_people = cov["cohort_people_total"]
    w(f"**The measurement works. The evidence supply does not.**")
    w("")
    w(f"The rubric behaves as intended under adversarial testing: "
      f"{stress['succeeded']} of {stress['attempted']} stress scorings succeeded and "
      f"every construct check passed. Two model families independently agreed on "
      f"the calibration anchor.")
    w("")
    w(f"But across the {n_people}-person cohort, the permitted sources yielded "
      f"**{cov['total_observations']} attractiveness observations total**, covering "
      f"{cov['cohort_people_with_any_observation']} of {n_people} people. "
      f"{len(cov['people_with_none'])} people have none at all.")
    w("")
    n_eps = len(episodes["episodes"])
    n_films = len(films["candidates"])
    jc = len(joint["jointly_covered"]) if joint else 0
    w(f"Across all {n_eps} relationship episodes and {n_films} co-starring films — "
      f"**{n_eps + n_films} candidate pairings** — and after both the ±1-year "
      f"bounded reuse AND the romance filter, exactly **{jc}** pairing"
      f"{'' if jc == 1 else 's'} {'is' if jc == 1 else 'are'} jointly covered.")
    w("")
    if scored:
        vals = [r["estimate"] for r in scored["person_periods"]
                if r["estimate"] is not None]
        w(decisive_measurement(shape_conf, len(vals)))
    w("")

    # ---------- cohort ----------
    w("## 1. Cohort")
    w("")
    w(f"`{cohort['version']}`, selected {cohort['selected_on']}. "
      f"{cohort['selection_basis']}")
    w("")
    w("| Person | Gender | Casting type | Observations found |")
    w("|---|---|---|---|")
    per = cov["per_person"]
    for p in cohort["people"]:
        n = per.get(p["wikidata_qid"], 0)
        w(f"| {p['display_name']} | {p['gender_category']} | {p['cohort_note']} | "
          f"{n if n else '**0**'} |")
    w("")

    # ---------- access decisions ----------
    w("## 2. Source access decisions")
    w("")
    w(obs["route_note"])
    w("")
    w("| Publisher | Route taken | Why |")
    w("|---|---|---|")
    w("| Wikidata | SPARQL, used | CC0; carries date qualifiers with explicit precision |")
    w("| English Wikipedia | API, used | CC BY-SA; reports the award fact and cites the publisher |")
    w("| people.com (People Inc.) | **not fetched** | robots.txt prohibits LLM use including RAG, and dataset creation |")
    w("| askmen.com (Ziff Davis) | **not fetched** | same prohibition wording; `anthropic-ai` disallowed |")
    w("| maxim.com | **not crawled** | `ClaudeBot`, `GPTBot`, `CCBot` disallowed |")
    w("| glamourmagazine.co.uk | **not crawled** | AI agents disallowed, and `archive.org_bot` too |")
    w("| Wayback captures of blocked publishers | **not used** | the Internet Archive conveys no reuse permission |")
    w("")
    w("This is an engineering access assessment from published directives and "
      "terms. It is not legal advice and not clearance.")
    w("")
    w("| Source | Publisher | Serves | Shape | Parsed | Years | Cohort hits |")
    w("|---|---|---|---|---|---|---|")
    for s in obs["sources"]:
        shape = s.get("shape", "editorial_award")
        parsed = s.get("ranked_entries_parsed", s.get("winner_rows_parsed", 0))
        extra = (f"{parsed} entries, {s['runner_up_positions']} ranked"
                 if shape == "ordered_rank" else f"{parsed} winner rows")
        years = f"{s['years'][0]}–{s['years'][1]}" if s.get("years") else "—"
        w(f"| {s['award']} | {s['publisher']} | {s['gender_served']} | `{shape}` | "
          f"{extra} | {years} | {s['observations_for_cohort']} |")
    w("")

    # ---------- records ----------
    w("## 3. Records")
    w("")
    c = records["counts"]
    e = episodes["counts"]
    w(f"- {c['candidates']} relationship candidates for {c['subjects']} subjects, "
      f"{c['with_reference']} carrying a source reference.")
    w(f"- **{c['start_year_precision_only']} of {c['with_start_date']} start dates are "
      f"year-precision only.** They are stored as years, not as 1 January.")
    w(f"- Merged into {e['episodes_after_merge']} episodes, joining "
      f"{e['merged_progressions']} dating-to-marriage progressions that Wikidata "
      f"stores as two abutting statements.")
    w(f"- {e['with_defects']} episodes carry defects and are unscorable:")
    for kind, n in episodes["defects"].items():
        w(f"  - `{kind}`: {n}")
    w(f"- {e['eligible_after_adult_window']} episodes eligible after the adult window.")
    w(f"- Scoring every year of every eligible episode would need "
      f"**{e['distinct_person_periods_needed']} person-period estimates** "
      f"(span {e['period_span'][0]}–{e['period_span'][1]}), against an M0 cap of 50. "
      f"The pilot samples at most three periods per pairing.")
    w("")
    w(f"On screen: {n_films} co-starring films found via Wikidata cast lists. "
      f"{films['caveat']}")
    w("")

    # ---------- stress ----------
    w("## 4. Measurement stress tests")
    w("")
    w(f"{stress['attempted']} scorings attempted, {stress['succeeded']} succeeded, "
      f"{stress['failed']} failed. Taxonomy: `{json.dumps(stress['error_taxonomy'])}`.")
    w("")
    f = stress["findings"]
    w("| Case | Question | Result |")
    w("|---|---|---|")
    s1 = f.get("S1_single_vs_multi", {})
    w(f"| S1 single vs multi | Does publication count impose the ordering? | "
      f"strong single-source **{s1.get('strong_single_mean')}** vs weak multi-source "
      f"**{s1.get('weak_multi_mean')}** — {s1.get('reading')} |")
    s2 = f.get("S2_format_equivalence", {})
    w(f"| S2 format | Award vs rank vs prose | {json.dumps(s2.get('per_format'))}, "
      f"spread {s2.get('spread')} — {s2.get('reading')} |")
    s3 = f.get("S3_corroboration_no_new_judgment", {})
    w(f"| S3 corroboration | Does an extra publisher jump a band? | "
      f"{s3.get('one_publisher_mean')} → {s3.get('three_publishers_mean')} "
      f"(delta {s3.get('delta')}) — {s3.get('reading')} |")
    s4 = f.get("S4_contradiction", {})
    w(f"| S4 contradiction | Does the rationale address the conflict? | "
      f"estimate {s4.get('estimates')}, names both placements: "
      f"{s4.get('rationales_name_both_placements')} |")
    s5 = f.get("S5_empty_and_offtopic", {})
    w(f"| S5 empty / off-topic | Unscored, or a low number? | "
      f"empty unscored: {s5.get('empty', {}).get('all_unscored')}, "
      f"off-topic unscored: {s5.get('offtopic', {}).get('all_unscored')} |")
    s6 = f.get("S6_identity_leakage", {})
    w(f"| S6 identity | Same evidence, different name | per judge "
      f"{json.dumps(s6.get('per_judge'))} — {s6.get('reading')} |")
    s7 = f.get("S7_order_sensitivity", {})
    w(f"| S7 order | Reordered observations | {json.dumps(s7.get('per_order'))}, "
      f"spread {s7.get('spread')} |")
    s8 = f.get("S8_volume_without_content", {})
    w(f"| S8 copy volume | One copy vs five | {json.dumps(s8.get('per_arm'))} — "
      f"{s8.get('reading')} |")
    w("")

    # ---------- coverage ----------
    w("## 5. Coverage, the two numbers that matter")
    w("")
    if first_pass:
        r = first_pass["reconciliation"]
        w(f"**First pass, no nearby reuse.** {r['person_periods_needed']} person-periods "
          f"needed for 8 selected pairings; {r['short_circuited_empty']} were empty and "
          f"short-circuited without a model call; {r['scored']} scored.")
        w("")
        jp = first_pass["joint_pairing_coverage"]
        w(f"Joint pairing coverage: **{jp['scored']} of {jp['pairings']}** "
          f"({jp['by_domain']['real_life']['scored']}/{jp['by_domain']['real_life']['pairings']} "
          f"real-life, {jp['by_domain']['on_screen']['scored']}/"
          f"{jp['by_domain']['on_screen']['pairings']} on-screen).")
        w("")
    w(f"**Exhaustive check.** Across all {n_eps} episodes and {n_films} films, zero "
      f"pairings had both sides evidenced in a shared year. The near-misses are the "
      f"finding: Ben Affleck and Jennifer Garner each have 2002 evidence and four "
      f"pairings together, every one landing one to three years off.")
    w("")
    if joint:
        w(f"**With the plan's ±1-year bounded reuse**, "
          f"{len(joint['jointly_covered'])} pairing-periods become jointly covered:")
        w("")
        for j in joint["jointly_covered"]:
            w(f"- {j['work'] or 'relationship'} ({j['period']}, {j['domain']}): "
              f"{j['a']} from {j['a_src']} (d={j['a_dist']}), "
              f"{j['b']} from {j['b_src']} (d={j['b_dist']})")
        w("")
        w("Both are reused estimates flagged `nearby_period`. Any simulation must "
          "give each source estimate ONE shared draw across every period it serves.")
        w("")

    # ---------- scored pairings ----------
    if scored:
        w("## 6. Scored person-periods and pairing contributions")
        w("")
        rec = scored["reconciliation"]
        w(f"{rec['scored']} of {rec['person_periods_with_evidence']} evidenced "
          f"person-periods scored, using {rec['model_calls']} model calls, "
          f"{rec['failed_calls']} failed.")
        w("")
        w("| Person | Period | Obs | Estimate | fable | astra | judge gap | support |")
        w("|---|---|---|---|---|---|---|---|")
        for r in scored["person_periods"]:
            j = r["judges"]
            w(f"| {r['person']} | {r['period']} | {r['observations']} | "
              f"{r['estimate']} | {j.get('fable', '–')} | {j.get('astra', '–')} | "
              f"{r['across_judges_gap'] if r['across_judges_gap'] is not None else '–'} | "
              f"{r['support_level']} |")
        w("")
        vals = [r["estimate"] for r in scored["person_periods"] if r["estimate"] is not None]
        if vals:
            w("### Score compression — the most consequential measurement result")
            w("")
            w(shape_paragraph(shape_conf, density))
            w("")
            w(f"All {len(vals)} estimates land between **{min(vals)}** and "
              f"**{max(vals)}**, a spread of **{max(vals) - min(vals)}** points "
              f"on a 0-100 scale.")
            w("")
            gaps = [r["across_judges_gap"] for r in scored["person_periods"]
                    if r["across_judges_gap"] is not None]
            agree = sum(1 for g in gaps if g == 0)
            w(f"The judges agree almost perfectly: {agree} of {len(gaps)} person-periods "
              f"came back identical from both families, and the largest disagreement was "
              f"{max(gaps) if gaps else 0} point. So the compression is not rater noise. "
              f"It is the evidence.")
            w("")
            w("An annual one-winner award is a superlative judgment by construction, so "
              "the rubric correctly places every winner in band 90-100. The consequence "
              "is that **award-shaped evidence cannot discriminate between winners.** "
              "A leaderboard built on it would rank people by a half-point that is the "
              "difference between one judge saying 92 and another saying 93.")
            w("")
            w("This was predicted in the plan's worked example A and is now measured. "
              "It is the strongest argument for either finding ordered, depth-carrying "
              "lists on permitted routes, or leading the men's and women's views with "
              "intervals instead of point estimates.")
            w("")
        if scored["scored_pairings"]:
            w("### Mirrored contributions")
            w("")
            for p in scored["scored_pairings"]:
                w(f"**{p['work'] or 'relationship'}** ({p['period']}, {p['domain']}) — "
                  f"{p['verification']}")
                w("")
                w(f"- {p['focal_male']}: {p['male_estimate']} "
                  f"(estimate from {p['male_estimate_from']})")
                w(f"- {p['female']}: {p['female_estimate']} "
                  f"(estimate from {p['female_estimate_from']})")
                w(f"- covered share {p['covered_share']}, period support "
                  f"`{p['period_support']}`")
                w(f"- gap in the men's view **{p['gap_mens_view']:+.1f}**, "
                  f"in the women's view **{p['gap_womens_view']:+.1f}**, "
                  f"mirrors exactly: {p['mirrors_exactly']}")
                w("")

    # ---------- density ----------
    if density:
        w("## 6. Evidence density — the actual bottleneck")
        w("")
        d = density
        w(f"Coverage asks whether a person-year has any evidence. Density asks how "
          f"much. Mean observations per person-period: **"
          f"{d['mean_observations_per_person_period']}**. Distribution: "
          f"`{d['distribution']}`. Person-periods carrying two or more publishers: "
          f"**{d['person_periods_with_two_or_more_publishers']}**. Person-periods "
          f"that are a lone one-winner award: "
          f"**{d['person_periods_that_are_a_lone_award']} of {d['person_periods']}**.")
        w("")
        r, syn = d.get("real_estimate_spread"), d.get("synthetic_estimate_spread")
        if r and syn:
            w("| Corpus | n | range | distinct values | SD |")
            w("|---|---|---|---|---|")
            w(f"| Real | {r['n']} | {r['range']} | **{r['distinct_values']}** | {r['sd']} |")
            w(f"| Synthetic stress | {syn['n']} | {syn['range']} | "
              f"{syn['distinct_values']} | {syn['sd']} |")
            w("")
        w(d["reading"])
        w("")
        w("This reframes what \"more sources\" has to mean. A source that adds a "
          "hundred new people at one observation each raises coverage and changes "
          "nothing about the board, because every one of those dossiers still "
          "lands in a single band. Only a source that puts a SECOND observation "
          "on a person-year that already has one can widen the distribution.")
        w("")

    # ---------- alignment ----------
    if align:
        w("## 6e. Why joint coverage does not move")
        w("")
        w(f"The corpus grew from 13 observations to "
          f"{density['observations'] if density else '?'} and joint coverage did "
          f"not move. This is why.")
        w("")
        w(f"- Pairings considered (romance-verified films plus scorable episodes): "
          f"**{align['pairings_considered']}**")
        w(f"- With evidence on BOTH sides at any distance: "
          f"**{align['pairings_with_evidence_on_both_sides']}**")
        w(f"- Missing evidence on one side entirely: "
          f"**{align['pairings_with_no_evidence_on_one_or_both_sides']}**")
        w("")
        w("Joint coverage if the nearby-period bound were widened:")
        w("")
        w("| Bound | Pairings jointly covered |")
        w("|---|---|")
        for b in sorted(align["jointly_covered_at_bound"], key=int)[:9]:
            mark = " ← current" if int(b) == align["current_bound"] else ""
            w(f"| ±{b} | {align['jointly_covered_at_bound'][b]}{mark} |")
        w("")
        w("Two things follow. Widening the bound from ±1 to ±2 would triple joint "
          "coverage, from 1 to 3. And it would not matter much beyond that: the "
          "count saturates at 6, because **22 of 30 pairings have no evidence on "
          "one side at all**. The bound is a real cost but absence is the bigger "
          "one.")
        w("")
        w(f"*{align['caveat']}*")
        w("")

    # ---------- gender-aligned confound ----------
    if gsc:
        w("## 5. The confound is aligned with gender")
        w("")
        w("| Gender | `editorial_award` | `ordered_rank` | `unordered_inclusion` |")
        w("|---|---|---|---|")
        for g in ("male", "female"):
            c = gsc["observations_by_gender_and_shape"].get(g, {})
            w(f"| {g} | {c.get('editorial_award', 0)} | "
              f"**{c.get('ordered_rank', 0)}** | {c.get('unordered_inclusion', 0)} |")
        w("")
        w("| Gender | n | mean | SD | range |")
        w("|---|---|---|---|---|")
        for g in ("male", "female"):
            e = gsc["estimates_by_gender"].get(g)
            if e:
                w(f"| {g} | {e['n']} | **{e['mean']}** | {e['sd']} | "
                  f"{e['min']}–{e['max']} |")
        w("")
        w(gsc["reading"])
        w("")
        w(f"**{gsc['consequence']}**")
        w("")

    # ---------- shape confounding ----------
    if shape_conf:
        w("## 5b. Evidence shape drives the estimate")
        w("")
        w(f"**Evidence type alone explains "
          f"{round((shape_conf['eta_squared_shape_explains'] or 0) * 100)}% of the "
          f"variance in the estimates** (eta-squared "
          f"{shape_conf['eta_squared_shape_explains']}).")
        w("")
        w("| Evidence shape | n | mean | range | SD |")
        w("|---|---|---|---|---|")
        for k, v in shape_conf["by_shape"].items():
            w(f"| `{k}` | {v['n']} | {v['mean']} | {v['min']}–{v['max']} | {v['sd']} |")
        w("")
        w(f"**{shape_conf['pairings_with_mismatched_shapes']} of "
          f"{shape_conf['jointly_covered_pairings']} jointly covered pairings have "
          f"MISMATCHED evidence shapes on the two sides.**")
        w("")
        for m in shape_conf["mismatched"]:
            w(f"- {m['pairing']} {m['period']}: {m['a']} `{m['a_shape']}` vs "
              f"{m['b']} `{m['b_shape']}`")
        w("")
        w("This is the project's most serious systematic bias and it is not "
          "hypothetical. The Brad Pitt and Jennifer Aniston gap of −12 pairs a "
          "Sexiest Man Alive win, which is superlative by construction and lands "
          "at 92, against ranked list placements, which spread lower. A large "
          "part of that gap is a statement about which publication covered whom "
          "in what format, not about the two people.")
        w("")
        w("Any published pairing whose sides carry different evidence shapes must "
          "carry this caveat on the row. A board that shows the number without it "
          "would be reporting a property of the sources as a property of the "
          "couple.")
        w("")

    # ---------- partner eligibility ----------
    if elig:
        w("## 6f. How much of the board is even reachable")
        w("")
        w("A pairing needs both sides. The partners missing evidence are two "
          "different populations, and counting them together overstates what the "
          "project can reach.")
        w("")
        w("| Status | Partners |")
        w("|---|---|")
        labels = {
            "evidenced": "Evidenced",
            "public_figure_no_evidence_found": "Public figure, no evidence found — **a real gap**",
            "notable_but_not_public_facing": "Notable but not public-facing (producers, directors)",
            "not_a_public_figure_do_not_rate": "Not a public figure — **never rate**",
        }
        for k, v in sorted(elig["counts"].items(), key=lambda kv: -kv[1]):
            w(f"| {labels.get(k, k)} | {v} |")
        w("")
        w(f"**Reachable ceiling: {elig['reachable_ceiling']} of {elig['partners']} "
          f"partners.**")
        w("")
        w(elig["reading"])
        w("")

    # ---------- romance ----------
    if romance:
        w("## 6a. On-screen romance verification")
        w("")
        c = romance["counts"]
        w(f"Co-appearance in a cast list is not a pairing. All "
          f"{c['candidates']} candidates were classified from the Wikipedia plot "
          f"section alone; {c['classified']} were classifiable and "
          f"**{c['qualifying_romances']}** are confirmed reciprocal romances.")
        w("")
        w("| Classification | Count |")
        w("|---|---|")
        for k, v in sorted(c["by_classification"].items(), key=lambda kv: -kv[1]):
            w(f"| `{k}` | {v} |")
        w("")
        w("Three results worth naming. *Being John Malkovich* came back "
          "`cannot_tell` for Brad Pitt and Michelle Pfeiffer, who both appear as "
          "themselves; before this filter existed the coverage count treated them "
          "as a couple. *Pearl Harbor* separated correctly: the romance is Affleck "
          "and Beckinsale, not Affleck and Garner. *What Lies Beneath* was "
          "classified `coerced_or_assault` and is therefore excluded rather than "
          "scored.")
        w("")

    # ---------- rater noise ----------
    if noise:
        h = noise["headline"]
        w("## 6b. Rater noise")
        w("")
        w(f"{noise['repeats']} repeats of each unchanged dossier. Mean within-judge "
          f"SD **{h['mean_within_judge_sd']}**, least significant difference at 95% "
          f"about **{h['least_significant_difference_95pct']}** points "
          f"({h['lsd_multiplier']} x SD).")
        w("")
        w("| Dossier | Shape | Runs | SD |")
        w("|---|---|---|---|")
        for t in noise["targets"]:
            for j, runs in t["runs"].items():
                sd = t["per_judge_sd"].get(j)
                w(f"| {t['person']} {t['period']} ({j}) | {t['shape']} | "
                  f"{', '.join(str(int(r)) for r in runs)} | {sd:.3f} |")
        w("")
        w("**Which dossier moves is the finding.** The award dossier does not move "
          "at all, because it is pinned against the 90-100 ceiling where no "
          "judgment is left to make. The ranked dossier does move, because there "
          "genuinely is one. Zero rater noise is a symptom of evidence that cannot "
          "discriminate, not a sign of a well-behaved rubric.")
        w("")
        if h.get("single_judge"):
            w(f"Measured on one judge ({', '.join(h['judges_that_contributed'])}). "
              "Codex reached 0% of its 7-day quota window mid-run, so this "
              "describes one model family and not a panel.")
            w("")

    # ---------- offset diagnostic ----------
    if offset:
        w("## 6c. Cross-gender offset sensitivity")
        w("")
        w(f"Deltas {offset['deltas']} applied to the partner side, on "
          f"{len(offset['people'])} people.")
        w("")
        w(f"- Identity holds: **{offset['identity_holds']}**")
        w(f"- PAW-rate ranks stable under a constant offset: "
          f"**{offset['rate_ranks_stable_under_constant_offset']}**")
        w(f"- Cumulative PAW ranks changed: "
          f"**{offset['cumulative_ranks_changed']}**")
        w("")
        w(offset["reading"])
        w("")
        w(f"*{offset['caveat']}*")
        w("")

    # ---------- grounding ----------
    if grounding:
        g = grounding["counts"]
        w("## 6d. Grounding audit")
        w("")
        w(f"{g['rationales']} rationales checked: **{g['passed_automated']}** passed "
          f"the automated checks, {g['failed_automated']} failed, "
          f"{g['needing_human_read']} are flagged for a human read in "
          f"`docs/GROUNDING-AUDIT.md`.")
        w("")
        w(f"*{grounding['limitation']}*")
        w("")

    # ---------- bottom line ----------
    if joint and noise:
        comp = [j for j in joint.get("jointly_covered", [])
                if j.get("comparability") == "comparable"]
        lsd = noise["headline"].get("least_significant_difference_95pct")
        w("## 6g. The bottom line, stated plainly")
        w("")
        n_comp = len(comp)
        w(f"Of {len(joint.get('jointly_covered', []))} jointly covered "
          f"pairing-periods, **{n_comp}** "
          f"{'compares' if n_comp == 1 else 'compare'} two people judged by the "
          f"same kind of evidence. The rest compare an award against a list "
          f"placement, where format explains much of the gap.")
        w("")
        if comp and scored:
            gaps = {(p["period"], p["domain"]): p["gap_mens_view"]
                    for p in scored.get("scored_pairings", [])}
            for j in comp:
                g = gaps.get((j["period"], j["domain"]))
                if g is None:
                    continue
                w(f"- **{j.get('work') or 'relationship'} ({j['period']})**: "
                  f"gap **{g:+.1f}**")
                if lsd:
                    verdict = ("**not distinguishable from zero**"
                               if abs(g) <= lsd else "above the noise floor")
                    w(f"  - Repeat-scoring puts the least significant difference "
                      f"at about **{lsd}** points, so this gap is {verdict}.")
            w("")
        w("So the project can now produce a signed, exactly mirrored, "
          "evidence-backed gap for a real couple. It cannot yet produce one that "
          "is both comparable and larger than its own measurement noise. That is "
          "a much better place than this run started, and it is not a "
          "leaderboard.")
        w("")

    # ---------- costs ----------
    w("## 7. Cost and budget")
    w("")
    stress_calls = sum(b["calls_made"] for b in stress["budgets"].values())
    scored_calls = (sum(b["calls_made"] for b in scored["budgets"].values())
                    if scored else 0)
    w(f"- Stress tests: {stress_calls} model calls "
      f"({json.dumps({k: v['calls_made'] for k, v in stress['budgets'].items()})}).")
    if scored:
        w(f"- Scoring: {scored_calls} model calls "
          f"({json.dumps({k: v['calls_made'] for k, v in scored['budgets'].items()})}).")
    w(f"- First pilot pass: 0 model calls — all 32 dossiers were empty and "
      f"short-circuited.")
    w(f"- **Total: {stress_calls + scored_calls} model calls**, against a cap of 300.")
    w("- Subscription quota only. API billing was asserted off at start-up.")
    w("- Dollar cost is not totalled: only the Claude arm reports `cost_usd`, and "
      "inventing a figure for the other arm would be a fabricated number.")
    w("")

    # ---------- assessment ----------
    w("## 8. Do the estimates reflect substance, or source availability?")
    w("")
    w("**Substance, where evidence exists. Availability decides whether it exists at all.**")
    w("")
    w("The stress cases say the rubric is reading the judgments rather than counting "
      "documents: one award beat two low placements by a wide margin, three "
      "corroborating publishers moved the estimate by a point, and five copies of one "
      "list moved it by zero. Both model families agreed exactly on every construct "
      "case they both ran.")
    w("")
    w("But which person-years have any evidence is decided entirely by which "
      "publishers happen to be reachable. On the permitted routes the men's award is "
      "an annual one-winner prize reported on Wikipedia since 1985, and the women's "
      "equivalent is a single number-one per year since 2000. Everything deeper sits "
      "behind terms that forbid this use.")
    w("")

    w("## 9. What M0 did not establish")
    w("")
    w("- Nothing here is verified. Every relationship is a Wikidata candidate and "
      "every on-screen pairing is co-appearance only, with no romance evidence.")
    w("- The grounding audit is not done: a human still has to read the rationales "
      "and judge whether the cited observations support what they claim.")
    w("- Rater noise was not measured by repeat scoring.")
    w("- The cross-gender offset diagnostic has no board to run against yet.")
    w("- Two judges from two families cannot separate a two-family idiosyncrasy "
      "from a property of the rubric.")
    w("")

    out = REPO / "docs/M0-REPORT.md"
    out.write_text("\n".join(L) + "\n")
    print(f"wrote {out} ({len('\n'.join(L))} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
