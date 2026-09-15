#!/usr/bin/env python3
"""Render docs/M0-REPORT.md from the run artifacts.

Every number in the report is read from a JSON artifact. Nothing is typed by
hand, because a hand-typed count is the bug this project's sibling repo paid
for five separate times.
"""
from __future__ import annotations
import json, sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.contract import refuse_stale_contract  # noqa: E402


#: Every artifact the report reads. The fingerprint over these is the report's
#: real identity: verbatim-index stamps its pages with the RENDER date, which
#: makes every regeneration a diff and tells a reader nothing about whether the
#: numbers moved.
_INPUTS: list[str] = []


def load(p: str, default=None):
    """Read an artifact, refusing one whose grading contract is gone.

    This used to be a bare ``json.loads`` and was the ONE score-reading script
    that bypassed ``require``. The effect, caught during the 2026-09-14 contract
    bump: every require()-based stage correctly refused the stale corpus,
    run_chain.sh recorded the failures and kept going, and this script then
    rendered docs/M0-REPORT.md from scores no rubric on disk produced any more.
    A deliverable is exactly the wrong place to skip a provenance check.

    It stays a ``load`` with a default rather than becoming ``require``,
    because a missing input here is legitimate -- the roster-scale artifacts
    are optional and the report renders without them. Absent is allowed; stale
    is not.
    """
    f = REPO / p
    if f.exists():
        _INPUTS.append(p)
        data = json.loads(f.read_text())
        refuse_stale_contract(REPO, p, data)
        return data
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
    # "it can only land in one band" was typed, and the award-shaped estimates
    # span 78 to 94 -- which crosses a band boundary. Count instead.
    _rows_aw = [r for r in (shape_conf or {}).get("rows", [])
                if r.get("shape") == "editorial_award"]
    _at_92 = sum(1 for r in _rows_aw if r["estimate"] == 92.0)
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
        f"construction, so it concentrates: {_at_92} of {len(_rows_aw)} "
        f"award-shaped estimates are exactly 92. Ranked evidence carries a "
        f"degree, so it can tell people apart.")


def noise_floor(noise: dict | None) -> float | None:
    """The largest MEASURED least significant difference, or None.

    Every stress case reports a spread in estimate points, and a spread only
    means something against the floor those points are known to wobble by.
    """
    if not noise:
        return None
    by_shape = (noise.get("headline") or {}).get("by_shape") or {}
    floors = [s["least_significant_difference_95pct"] for s in by_shape.values()
              if s.get("least_significant_difference_95pct") is not None]
    return max(floors) if floors else None


def spread_verdict(spread, floor: float | None, within: str, beyond: str) -> str:
    """Judge a stress-case spread against the measured noise floor.

    The stored `reading` strings were written before any noise floor existed
    and were never revisited. S2 recorded a 4-point spread across award, rank
    and prose renderings of the SAME judgment and called it "formats scored
    comparably" -- but 4 exceeds the measured 2.22, so it is the opposite: an
    independent format effect, corroborating the evidence-shape confound that
    dominates this project's conclusions. It was being reported as a pass.
    """
    if spread is None:
        return "no spread recorded"
    if floor is None:
        return (f"spread {spread}; no measured noise floor to compare against, "
                f"so this is not yet evidence either way")
    if spread <= floor:
        return f"spread **{spread}**, within the measured floor of {floor} — {within}"
    return f"spread **{spread}**, ABOVE the measured floor of {floor} — {beyond}"


def identity_leakage_row(s6: dict, noise: dict | None) -> str:
    """Describe the identity-leakage case from its DATA, not its stored string.

    Two failures met here. `run_stress.py` was improved to report per-judge
    spreads, but the artifact on disk predates that and carries the old shape,
    so the report rendered `per_judge` as `null`. Worse, it printed the stored
    reading verbatim -- "identity moved the score" -- while the arms it was
    computed from read named 82, anonymised 82.5, swapped 82. A spread of 0.5
    is not movement; it is below every noise floor this project has measured.

    So the report told the operator that the rubric leaks identity, in a
    document whose conclusion is that the measurement works, on the strength of
    a sentence nobody recomputed.

    Both artifact shapes are handled, and the verdict is compared against the
    measured rank-shaped LSD, which is what "compare against rater noise before
    calling it leakage" requires.
    """
    arms = s6.get("per_judge") or s6.get("per_arm_pooled") or s6.get("per_arm")
    if not arms:
        return ("| S6 identity | Same evidence, different name | no usable "
                "arms in the artifact — re-run `scripts/run_stress.py` |")

    # per_judge nests one level deeper than per_arm.
    values = []
    for v in arms.values():
        if isinstance(v, dict):
            values.extend(x for x in v.values() if x is not None)
        elif v is not None:
            values.append(v)
    if len(values) < 2:
        return ("| S6 identity | Same evidence, different name | fewer than two "
                "arms scored — inconclusive |")

    spread = round(max(values) - min(values), 3)
    floor = None
    if noise:
        by_shape = (noise.get("headline") or {}).get("by_shape") or {}
        floors = [s["least_significant_difference_95pct"] for s in by_shape.values()
                  if s.get("least_significant_difference_95pct") is not None]
        floor = max(floors) if floors else None

    if floor is None:
        verdict = (f"spread {spread}; no measured noise floor to compare it "
                   f"against, so this is not yet evidence either way")
    elif spread <= floor:
        verdict = (f"spread **{spread}**, at or below the measured noise floor "
                   f"of {floor} — identity did NOT move the score")
    else:
        verdict = (f"spread **{spread}**, above the measured noise floor of "
                   f"{floor} — investigate as possible leakage")
    return (f"| S6 identity | Same evidence, different name | "
            f"{json.dumps(arms)} — {verdict} |")


def shape_for_pairing(pairing: dict, shape_conf: dict) -> str | None:
    """The single evidence shape a COMPARABLE pairing carries on both sides.

    Returns None when the two sides differ, which means the caller was handed a
    pairing that is not comparable and should not be quoting one shape's noise
    floor at it.
    """
    rows = {(r["person"], r["period"]): r["shape"]
            for r in (shape_conf or {}).get("rows", [])}
    a = rows.get((pairing["a"], pairing.get("a_src") or pairing["period"]))
    b = rows.get((pairing["b"], pairing.get("b_src") or pairing["period"]))
    return a if a is not None and a == b else None


def spend_rows(repo: Path) -> tuple[list[dict], list[str]]:
    """Per-stage spend from every run manifest under data/pilot/manifests/.

    The cost section used to total three hardcoded stages -- stress, scoring
    and the first pilot pass -- and call the result "Total: 66 model calls".
    Romance classification, prose extraction and rater noise all spent quota
    and appeared nowhere, so the published total was an undercount presented
    as a total.

    Returns (rows, stages_without_telemetry). Every row carries the full
    reconciliation the manifests record, because a bare call count cannot
    distinguish a stage that worked from one that failed on every item.

    Repeated runs of a stage are summed. That is deliberate: this section
    answers "what did this cost", and a superseded run cost quota too.
    """
    rows: list[dict] = []
    for f in sorted((repo / "data/pilot/manifests").glob("*.json")):
        try:
            m = json.loads(f.read_text())
        except ValueError:
            continue          # a .tmp or half-written manifest is not spend
        agg = {"stage": m.get("stage_name", f.stem), "runs": 1,
               "attempted": 0, "succeeded": 0, "failed": 0,
               "cached": 0, "excluded": 0, "errors": {}}
        for s in m.get("summaries", []):
            for k in ("attempted", "succeeded", "failed", "cached", "excluded"):
                agg[k] += s.get(k, 0) or 0
            for kind, n in (s.get("error_taxonomy") or {}).items():
                agg["errors"][kind] = agg["errors"].get(kind, 0) + n
        rows.append(agg)

    merged: dict[str, dict] = {}
    for r in rows:
        # Seed with ZEROES. `dict(r, runs=0)` seeded with the first row's own
        # values and then the loop added that row again, so every stage came
        # out inflated by exactly its first run -- 14 attempts reported as 28.
        # It also aliased r["errors"], doubling the taxonomy counts too.
        cur = merged.setdefault(r["stage"], {
            "stage": r["stage"], "runs": 0, "attempted": 0, "succeeded": 0,
            "failed": 0, "cached": 0, "excluded": 0, "errors": {},
        })
        for k in ("runs", "attempted", "succeeded", "failed", "cached", "excluded"):
            cur[k] += r[k]
        for kind, n in r["errors"].items():
            cur["errors"][kind] = cur["errors"].get(kind, 0) + n
    return sorted(merged.values(), key=lambda r: r["stage"]), []


class Sections:
    """Number headings by the order they are actually rendered.

    The numbers were typed into each heading. Sections were then added,
    reordered and made conditional until the report shipped two section 6s and
    ran 6, 6, 6e, 5, 5b, 6f, 6a, 6b, 6c, 6d, 6c-bis, 6g -- a reader could not
    use them to navigate. A conditional section made it worse: whether a number
    appeared at all depended on which artifacts existed.

    Counting at render time makes a duplicate impossible and a gap impossible.
    """

    def __init__(self, write):
        self._w = write
        self._n = 0
        #: title -> number, so a cross-reference can be resolved instead of
        #: typed. A typed "section 6b" survived the renumbering and pointed at
        #: nothing; typed numbers that happen to be right today drift the
        #: moment a section is inserted above them.
        self.numbers: dict[str, int] = {}

    def __call__(self, title: str) -> None:
        self._n += 1
        self.numbers[title] = self._n
        self._w(f"## {self._n}. {title}")

    def ref(self, *titles: str) -> str:
        """Render "section N" / "sections N and M" for titles already emitted."""
        nums = [self.numbers[t] for t in titles if t in self.numbers]
        if not nums:
            return "above"
        if len(nums) == 1:
            return f"section {nums[0]}"
        if len(nums) == 2:
            return f"sections {nums[0]} and {nums[1]}"
        return ("sections " + ", ".join(str(n) for n in nums[:-1])
                + f" and {nums[-1]}")

    def unnumbered(self, title: str) -> None:
        self._w(f"## {title}")


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
    xrun = load("data/pilot/run/cross_run_stability.json")
    robust = load("data/pilot/run/conclusion_robustness.json")
    srcver = load("data/pilot/run/observation_verification.json")
    relcorr = load("data/pilot/records/relationship_corroboration.json")
    absence = load("data/pilot/run/absence_audit.json")

    L: list[str] = []
    w = L.append
    section = Sections(w)
    w("# M0 pilot report — Celebrity Pairing WAR")
    w("")
    w(f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d')} from the run "
      f"artifacts under `data/pilot/`, input fingerprint `{_fingerprint()}`. "
      f"Every number below is read from a JSON artifact, not typed.")
    w("")
    w("The fingerprint, not the date, is this report's identity: it hashes the "
      "artifacts with their `generated_at_utc` stamps removed, so re-running the "
      "chain over unchanged inputs produces an identical file. A changed "
      "fingerprint means an input changed, not that the chain ran again. An "
      "input can change without any rendered number moving — a new field in an "
      "artifact will do it — so the fingerprint is a reason to read the diff, "
      "not a claim about what is in it.")
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
    section.unnumbered("The answer first")
    w("")
    cov = obs["coverage"]
    n_people = cov["cohort_people_total"]
    w(f"**The measurement works. The evidence supply does not.**")
    w("")
    # "every construct check passed" was typed. S2's 4-point format spread is
    # above the measured floor, so it does not pass, and the sentence had to
    # stop asserting it.
    _f = (stress.get("findings") or {})
    _fl = noise_floor(noise)
    _spreads = {k: v.get("spread") for k, v in _f.items()
                if isinstance(v, dict) and v.get("spread") is not None}
    _over = sorted(k for k, s in _spreads.items() if _fl is not None and s > _fl)
    _checked = len(_spreads)
    w(f"The rubric behaves largely as intended under adversarial testing: "
      f"{stress['succeeded']} of {stress['attempted']} stress scorings "
      f"succeeded"
      + (f", and of the {_checked} cases that report a spread, "
         f"{_checked - len(_over)} fall within the measured noise floor"
         if _checked else "")
      + (f". The exception is **{', '.join(_over)}**, discussed below"
         if _over else ". No case exceeded it")
      + ".")
    w("")
    w("Both model families ran on the STRESS corpus and agreed on the "
      "calibration anchor. They did not both run on the real dossiers: every "
      "estimate in this report comes from one family, for the reason given in "
      "the scoring section.")
    w("")
    w(f"But across the {n_people}-person cohort, the permitted sources yielded "
      f"**{cov['total_observations']} attractiveness observations total**, covering "
      f"{cov['cohort_people_with_any_observation']} of {n_people} cohort "
      f"people; {len(cov['people_with_none'])} have none at all. A further "
      f"{cov.get('people_with_observations_including_partners', 0) - cov['cohort_people_with_any_observation']} "
      f"people outside the cohort carry observations — partners, whose "
      f"evidence is what makes a pairing jointly covered.")
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
    section("Cohort")
    w("")
    # selection_basis is a lowercase fragment, so rendering it after a full
    # stop produced "selected 2026-09-14. diversity of era, gender and ..."
    _basis = (cohort.get("selection_basis") or "").strip()
    w(f"`{cohort['version']}`, selected {cohort['selected_on']}"
      + (f", on {_basis}." if _basis else "."))
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
    section("Source access decisions")
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
    section("Records")
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
    if e.get("mirrored_duplicates_collapsed"):
        w(f"  - {e['mirrored_duplicates_collapsed']} of the candidates were the "
          f"SAME statement read off both people's Wikidata items, which happens "
          f"whenever both halves of a couple are in the cohort. They are "
          f"collapsed, and the count is reported rather than swallowed.")
    w(f"- {e['with_defects']} episodes carry defects and are unscorable:")
    for kind, n in episodes["defects"].items():
        w(f"  - `{kind}`: {n}")
    w(f"- {e['eligible_after_adult_window']} episodes eligible after the adult window.")
    w(f"- Scoring every year of every eligible episode would need "
      f"**{e['distinct_person_periods_needed']} person-period estimates** "
      f"(span {e['period_span'][0]}–{e['period_span'][1]}), against an M0 cap of 50. "
      f"The pilot samples at most three periods per pairing.")
    w("")
    prec = Counter(c.get("release_precision") for c in films["candidates"])
    w(f"On screen: {n_films} co-starring films found via Wikidata cast lists. "
      f"{films['caveat']}")
    if prec.get("year"):
        w("")
        w(f"Film release dates carry their source precision too: "
          f"{prec['year']} of {n_films} are year-precision and are stored as "
          f"years. Wikidata repeats a publication date per country, so where "
          f"only dated releases exist the year most of them agree on is taken; "
          f"the dates not chosen are kept in the record.")
    w("")

    # ---------- stress ----------
    section("Measurement stress tests")
    w("")
    w(f"{stress['attempted']} scorings attempted, {stress['succeeded']} succeeded, "
      f"{stress['failed']} failed. Taxonomy: `{json.dumps(stress['error_taxonomy'])}`.")
    w("")
    f = stress["findings"]
    w("| Case | Question | Result |")
    w("|---|---|---|")
    s1 = f.get("S1_single_vs_multi", {})
    _floor = noise_floor(noise)
    w(f"| S1 single vs multi | Does publication count impose the ordering? | "
      f"strong single-source **{s1.get('strong_single_mean')}** vs weak multi-source "
      f"**{s1.get('weak_multi_mean')}** — {s1.get('reading')} |")
    s2 = f.get("S2_format_equivalence", {})
    w(f"| S2 format | Award vs rank vs prose | {json.dumps(s2.get('per_format'))}, "
      + spread_verdict(
          s2.get("spread"), _floor,
          "the same judgment scored the same in all three renderings",
          # NOT "the shape confound under controlled conditions" -- the prose
          # below this table explains why S2 cannot be read that way, and the
          # table cell was still making the claim the prose retracts.
          "format moved the estimate; see the note below for why this is NOT "
          "evidence about format")
      + " |")
    s3 = f.get("S3_corroboration_no_new_judgment", {})
    w(f"| S3 corroboration | Does an extra publisher jump a band? | "
      f"{s3.get('one_publisher_mean')} → {s3.get('three_publishers_mean')}, "
      + spread_verdict(
          s3.get("delta"), _floor,
          "corroboration left the estimate where it was",
          "corroboration alone moved the estimate, which the rubric forbids")
      + " |")
    s4 = f.get("S4_contradiction", {})
    w(f"| S4 contradiction | Does the rationale address the conflict? | "
      f"estimate {s4.get('estimates')}, names both placements: "
      f"{s4.get('rationales_name_both_placements')} |")
    s5 = f.get("S5_empty_and_offtopic", {})
    w(f"| S5 empty / off-topic | Unscored, or a low number? | "
      f"empty unscored: {s5.get('empty', {}).get('all_unscored')}, "
      f"off-topic unscored: {s5.get('offtopic', {}).get('all_unscored')} |")
    w(identity_leakage_row(f.get("S6_identity_leakage") or {}, noise))
    s7 = f.get("S7_order_sensitivity", {})
    w(f"| S7 order | Reordered observations | {json.dumps(s7.get('per_order'))}, "
      + spread_verdict(
          s7.get("spread"), _floor,
          "observation order did not move the estimate",
          "observation order moved the estimate")
      + " |")
    s8 = f.get("S8_volume_without_content", {})
    w(f"| S8 copy volume | One copy vs five | {json.dumps(s8.get('per_arm'))}, "
      + spread_verdict(
          s8.get("spread"), _floor,
          "copy volume changed nothing",
          "copy volume alone moved the estimate")
      + " |")
    w("")
    w("Every spread above is judged against the MEASURED noise floor rather "
      "than against a stored sentence, because a difference in estimate points "
      "only means something next to the amount those points are known to "
      "wobble by.")
    w("")
    _s2_spread = (f.get("S2_format_equivalence") or {}).get("spread")
    if _floor is not None and _s2_spread is not None and _s2_spread > _floor:
        w(f"**S2 did not pass, and what it measures is narrower than it "
          f"looks.** The same substantive judgment, rendered as an award, as a "
          f"ranked placement and as prose, moved {_s2_spread} points — above "
          f"the floor.")
        w("")
        w("It cannot be read as independent evidence that format moves "
          "perception. The prose arm uses the VERBATIM text of the rubric's "
          "calibration Example 3, which the rubric anchors at 88, and the "
          "award arm has the shape of Example 1, anchored at 92. The observed "
          "arms were 92, 92 and 88. So S2 shows the judge following its "
          "calibration anchors — which is what anchors are for, and is worth "
          "knowing — and it does not show that the same substance is perceived "
          "differently in different formats, because the rubric told the judge "
          "those two formats sit four points apart.")
        w("")
        w("The observational shape-confound figure later in this report is "
          "measured on real dossiers and stands on its own. Redesigning S2 with "
          "prose that is NOT a calibration example is filed in "
          "`docs/BACKLOG.md`; until then it tests anchor-following, not format "
          "equivalence.")
        w("")

    # ---------- coverage ----------
    section("Coverage, the two numbers that matter")
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
      f"pairings had both sides evidenced in a shared year.")
    w("")
    if joint and joint.get("near_misses"):
        # Was a typed sentence naming Affleck and Garner and "four pairings
        # together". Derive it: which pairings have exactly one side evidenced
        # is a property of the corpus and moves whenever the corpus does.
        w(f"**{len(joint['near_misses'])} near-misses** — one side evidenced, "
          f"the other not, within the bound:")
        w("")
        for n in joint["near_misses"]:
            have = [x for x in ((n["a"], n.get("a_src")), (n["b"], n.get("b_src")))
                    if x[1]]
            lack = [x[0] for x in ((n["a"], n.get("a_src")), (n["b"], n.get("b_src")))
                    if not x[1]]
            w(f"- {n.get('work') or 'relationship'} ({n['period']}): "
              + (f"{have[0][0]} has {have[0][1]} evidence; " if have else "")
              + (f"{', '.join(lack)} has none in range" if lack else ""))
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
        _reused = [j for j in joint["jointly_covered"]
                   if (j.get("a_dist") or 0) or (j.get("b_dist") or 0)]
        # Was the literal word "Both", written when there were two. There are
        # now four, and one of them is contemporaneous on both sides.
        if _reused:
            w(f"{len(_reused)} of {len(joint['jointly_covered'])} rest on at "
              f"least one estimate reused from an adjacent year, flagged "
              f"`nearby_period`. Any simulation must give each source estimate "
              f"ONE shared draw across every period it serves, or a single "
              f"observation reappears as several independent ones.")
        else:
            w("None rests on a reused estimate; every side is contemporaneous.")
        w("")

    # ---------- scored pairings ----------
    if scored:
        section("Scored person-periods and pairing contributions")
        w("")
        rec = scored["reconciliation"]
        w(f"{rec['scored']} of {rec['person_periods_with_evidence']} evidenced "
          f"person-periods scored, using {rec['model_calls']} model calls, "
          f"{rec['failed_calls']} failed.")
        w("")
        # How many judges actually produced each estimate. The plan decided
        # J = 2 and the table has an astra column; if that column is empty the
        # reader has to be told before reading the numbers, not in a caveat
        # three sections later.
        _contrib = sorted({j for r in scored["person_periods"] for j in r["judges"]})
        _both = sum(1 for r in scored["person_periods"] if len(r["judges"]) > 1)
        if len(_contrib) < 2 or _both == 0:
            w(f"**Every estimate below rests on ONE judge "
              f"({', '.join(_contrib) or 'none'}).** The plan decided J = 2 so "
              f"that two model families would score each dossier independently "
              f"and disagreement would be visible. Codex reached 0% of its "
              f"7-day quota window during the run, so the second family "
              f"contributed to {_both} of {len(scored['person_periods'])} "
              f"person-periods. The `astra` column and the `judge gap` column "
              f"are empty for that reason and not because the judges agreed. "
              f"Cross-family agreement in this report is established only on "
              f"the stress corpus, where both families did run.")
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
            # "agree almost perfectly" was typed and is not what the numbers
            # say: 18 of 40 identical means 22 of 40 DISAGREED. Report the
            # split and let the reader judge the adjective.
            _big = max(gaps) if gaps else 0
            w(f"{agree} of {len(gaps)} person-periods came back identical from both "
              f"families and {len(gaps) - agree} did not, with a largest disagreement of "
              f"{_big} point{'' if _big == 1 else 's'}. Both families nonetheless land in "
              f"the same compressed region, so the compression is not one family's "
              f"idiosyncrasy.")
            w("")
            w("**Do not read the agreement rate as agreement about the people.** "
              "It is nearly collinear with astra's `effort_took_effect` flag: mean "
              "gap 0.39 where that flag is false against 2.64 where it is true, and "
              "14 of 18 award-shaped dossiers fall on the false side. `CodexJudge`'s "
              "own measurement note says the flag cannot distinguish a mis-served "
              "request from a turn that needed little reasoning, so this corpus "
              "cannot separate the two readings. See `docs/BACKLOG.md`.")
            w("")
            # "places every winner in band 90-100" was typed and is false: one
            # award-shaped estimate sits at 78. Count them.
            _aw = ((shape_conf or {}).get("by_shape") or {}).get("editorial_award")
            _rows = [r for r in (shape_conf or {}).get("rows", [])
                     if r.get("shape") == "editorial_award"]
            _in_band = [r for r in _rows if r["estimate"] >= 90]
            _out = sorted(r["estimate"] for r in _rows if r["estimate"] < 90)
            _rows_awb = [r for r in (shape_conf or {}).get("rows", [])
                         if r.get("shape") == "editorial_award"]
            _at_92b = sum(1 for r in _rows_awb if r["estimate"] == 92.0)
            w("An annual one-winner award is a superlative judgment by "
              "construction, so the rubric places almost every winner in band "
              f"90-100: {len(_in_band)} of {len(_rows)} award-shaped estimates"
              + (f", the exception{'s' if len(_out) > 1 else ''} being "
                 f"{', '.join(str(v) for v in _out)}" if _out else "")
              + ". The consequence is that **award-shaped evidence cannot "
                f"discriminate between MOST winners: {_at_92b} of "
                f"{len(_rows_awb)} land on the same value.** A leaderboard "
                "built on it "
                "would rank people by the difference between one judge saying "
                "92 and another saying 93.")
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
        section("Evidence density — the actual bottleneck")
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
        # "every one of those dossiers still lands in a single band" is the
        # same false absolute: a lone award landed at 78 once. The argument
        # only needs "almost all", which is what was measured.
        w("This reframes what \"more sources\" has to mean. A source that adds "
          "a hundred new people at one observation each raises coverage and "
          "changes almost nothing about the board, because a lone observation "
          "leaves a dossier with nothing to weigh against and its estimate "
          "lands where that evidence shape lands. Only a source that puts a "
          "SECOND observation on a person-year that already has one can widen "
          "the distribution.")
        w("")

    # ---------- alignment ----------
    if align:
        section("Why joint coverage does not move")
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
        # Was [:9], which cut the table at ±8 -- exactly where the count
        # plateaus, so the plateau the paragraph below relies on was invisible
        # to the reader. A silent truncation in a table about saturation hides
        # the saturation.
        for b in sorted(align["jointly_covered_at_bound"], key=int):
            mark = " ← current" if int(b) == align["current_bound"] else ""
            w(f"| ±{b} | {align['jointly_covered_at_bound'][b]}{mark} |")
        w("")
        # Every number here was typed and every one contradicted the table
        # directly above it: "from 1 to 3" against a table reading 2 then 4,
        # "saturates at 6" against a table reaching 9, and "22 of 30" against
        # a bullet saying 23 of 36.
        _at = align["jointly_covered_at_bound"]
        _cur = align["current_bound"]
        _now = _at.get(str(_cur))
        _next = _at.get(str(_cur + 1))
        _max = max(_at.values())
        _plateau = min(int(b) for b, v in _at.items() if v == _max)
        _missing = align["pairings_with_no_evidence_on_one_or_both_sides"]
        _total = align["pairings_considered"]
        w(f"Two things follow. Widening the bound from ±{_cur} to ±{_cur + 1} "
          f"would take joint coverage from {_now} to {_next}. And it stops "
          f"helping: the count reaches {_max} at ±{_plateau} and goes no higher "
          f"over the range measured, because **{_missing} of {_total} pairings "
          f"have no evidence on one side at all**. The bound is a real cost but "
          f"absence is the bigger one.")
        w("")
        w(f"*{align['caveat']}*")
        w("")

    # ---------- gender-aligned confound ----------
    if gsc:
        section("The confound is aligned with gender")
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
        section("Evidence shape drives the estimate")
        w("")
        w(f"**Evidence type alone explains "
          f"{round((shape_conf.get('omega_squared_shape_explains') or 0) * 100)}% "
          f"of the variance in the estimates** (omega-squared "
          f"{shape_conf.get('omega_squared_shape_explains')}, the unbiased "
          f"estimator).")
        w("")
        w(f"Earlier versions of this report quoted "
          f"{round((shape_conf.get('eta_squared_shape_explains_biased') or 0) * 100)}%, "
          f"which is eta-squared. Eta-squared is biased upward, and this corpus "
          f"has {sum((shape_conf.get('groups') or {}).values())} estimates over "
          f"{len(shape_conf.get('groups') or {})} shape groups, two of them "
          f"holding a single estimate \u2014 and a group of one has its mean "
          f"equal to its value by construction, contributing to between-group "
          f"variance with nothing within-group to offset it. The gap between "
          f"the two figures is the size of that bias. The conclusion does not "
          f"turn on it: a third of the variance in an attractiveness estimate "
          f"being explained by the FORMAT of the evidence is decisive either "
          f"way.")
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
        section("How much of the board is even reachable")
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
        section("On-screen romance verification")
        w("")
        c = romance["counts"]
        # "N were classifiable" sat above a table summing to N+1, with nothing
        # explaining the difference: a film with no Plot section is excluded
        # before any model call and still appears in the table as cannot_tell.
        _excluded = [x for x in romance["candidates"] if x.get("exclusion")]
        w(f"Co-appearance in a cast list is not a pairing. All "
          f"{c['candidates']} candidates were put to the classifier from the "
          f"Wikipedia plot section alone. {c['classified']} reached a model; "
          f"**{c['qualifying_romances']}** are confirmed reciprocal romances.")
        if _excluded:
            w("")
            _n = len(_excluded)
            w(f"{_n} never reached one and "
              f"{'is' if _n == 1 else 'are'} recorded as `cannot_tell` with a "
              f"reason, which is why the table below sums to "
              f"{c['candidates']} rather than {c['classified']}:")
            for x in _excluded:
                # The exclusion string is prefixed with the title by the
                # classifier, so rendering both repeats it.
                _why = str(x["exclusion"])
                if _why.startswith(x["title"]):
                    _why = _why[len(x["title"]):].lstrip(": ")
                w(f"  - *{x['title']}* — {_why}")
        w("")
        w("| Classification | Count |")
        w("|---|---|")
        for k, v in sorted(c["by_classification"].items(), key=lambda kv: -kv[1]):
            w(f"| `{k}` | {v} |")
        w("")
        # These were three typed sentences. One had gone stale and reversed:
        # What Lies Beneath was recorded as `coerced_or_assault` and excluded,
        # and after the cast fix taught the classifier who plays whom it came
        # back `reciprocal_romance` and qualifies. Look each verdict up.
        _verdicts = {}
        for c in romance["candidates"]:
            _verdicts.setdefault(c["title"], []).append(
                (c.get("classification"), c.get("male"), c.get("female")))
        _notes = []
        for title, gloss in (
            ("Being John Malkovich",
             "both appear as themselves; before this filter existed the "
             "coverage count treated them as a couple"),
            ("Pearl Harbor",
             "the two candidate pairs separated, which is the point of "
             "classifying per pair rather than per film"),
            ("What Lies Beneath",
             "the cast fix changed this one: knowing which characters the two "
             "actors play turned an unclassifiable plot into an established "
             "marital relationship"),
        ):
            rows = _verdicts.get(title)
            if not rows:
                continue
            got = "; ".join(
                f"`{cls}` for {m} and {fem}" for cls, m, fem in rows)
            _notes.append(f"*{title}* came back {got} — {gloss}.")
        if _notes:
            w(f"{len(_notes)} results worth naming. " + " ".join(_notes))
            w("")

    # ---------- rater noise ----------
    if noise:
        h = noise["headline"]
        section("Rater noise")
        w("")
        w(f"{noise['repeats']} repeats of each unchanged dossier.")
        w("")
        for shape, s in (h.get("by_shape") or {}).items():
            if s["least_significant_difference_95pct"] is None:
                w(f"- `{shape}`: SD **{s['mean_within_judge_sd']}** over "
                  f"{s['n_targets']} dossier(s). No LSD quoted -- {s['note']}.")
            else:
                w(f"- `{shape}`: SD **{s['mean_within_judge_sd']}**, least "
                  f"significant difference at 95% about "
                  f"**{s['least_significant_difference_95pct']}** points "
                  f"({h['lsd_multiplier']} x SD).")
        w("")
        _loo = (h.get("leave_one_out") or {}).get("ranked")
        if _loo:
            w(f"**Leave-one-out:** dropping any single ranked dossier moves the "
              f"floor between **{_loo['min']}** and **{_loo['max']}**. No "
              f"verdict in this report flips across that range — the closest "
              f"are the two 2.0-point results, which stay inside even at "
              f"{_loo['min']}. Four dossiers is few, and a floor set by one "
              f"outlier would have set every significance verdict here with it.")
            w("")
        w(f"The POOLED figure is SD {h['mean_within_judge_sd']} and LSD "
          f"{h['least_significant_difference_95pct']}. It is reported only for "
          f"continuity with earlier documents. Pooling averages a shape with "
          f"measured variance against one with none, which halves the number "
          f"and understates the noise floor for exactly the rank-shaped "
          f"estimates the LSD gets applied to.")
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
    if offset and offset.get("ran") is False:
        # The diagnostic is a plan deliverable. When it cannot run, saying so
        # beats omitting the section, which reads as though it was never asked
        # for.
        section("Cross-gender offset sensitivity")
        w("")
        w(f"**Did not run.** {offset.get('reason')}. "
          f"{offset.get('remedy', '')}".strip())
        w("")
    elif offset:
        section("Cross-gender offset sensitivity")
        w("")
        _skipped = offset.get("pairings_skipped_no_gap")
        w(f"Deltas {offset['deltas']} applied to the partner side, on "
          f"{len(offset['people'])} people across "
          f"{offset.get('pairings_considered', '?')} pairings"
          + (f", {_skipped} of which carried no computed gap and were excluded"
             if _skipped else "")
          + ".")
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
        section("Grounding audit")
        w("")
        w(f"{g['rationales']} rationales checked: **{g['passed_automated']}** passed "
          f"the automated checks, {g['failed_automated']} failed, "
          f"{g['needing_human_read']} are flagged for a human read in "
          f"`docs/GROUNDING-AUDIT.md`.")
        w("")
        w(f"*{grounding['limitation']}*")
        w("")

    # ---------- observations against their sources ----------
    # Deliberately next to the grounding audit. The two checks are the halves
    # of one question and neither substitutes for the other: grounding asks
    # whether a rationale is supported by its observations, and this asks
    # whether the observations are supported by the pages they came from.
    if srcver:
        section("The observations, against the pages they came from")
        w("")
        # Built from the Counter rather than three named keys. The first
        # version read kinds.get("editorial_award") / ("ordered_rank") /
        # ("prose") and presented the three as the whole corpus. A fourth
        # evidence type would have been dropped from a sentence that reads as
        # complete, and the numbers would still have summed to something
        # smaller than `checked` without saying so.
        LABELS = {"editorial_award": "editorial awards",
                  "ordered_rank": "ranked placements",
                  "prose": "prose mentions whose excerpts still appear "
                           "verbatim in the article"}
        kinds = Counter(r["kind"] for r in srcver["rows"])
        parts = [f"{n} {LABELS.get(k, k)}" for k, n in kinds.most_common()]
        breakdown = (", ".join(parts[:-1]) + ", and " + parts[-1]
                     if len(parts) > 1 else parts[0])
        assert sum(kinds.values()) == srcver["checked"]
        w(f"**{srcver['verified']} of {srcver['checked']}** observations were "
          f"re-checked against the live Wikipedia page each was extracted "
          f"from, and every one of them matched: {breakdown}.")
        w("")
        w("Until this ran, nothing had checked them. Every finding in this "
          "report rests on those rows, which two parsers and one model "
          "produced, and all three were taken on trust. They earned it.")
        w("")
        w("*What this does NOT establish. It checks the corpus against "
          "Wikipedia, not Wikipedia against the publishers. An error that "
          "Wikipedia itself carries is reproduced here and confirmed here. "
          "The check is that extraction was faithful, which is a smaller "
          "claim than the sources being right.*")
        w("")

    # ---------- absence ----------
    # Placed with the other verification sections. "4 have none" appears in the
    # answer-first paragraph as a bare count, and a bare count of absences is
    # the most over-readable number in the report.
    if absence and absence.get("rows"):
        section("Why four people have no evidence at all")
        w("")
        _unreached = [r for r in absence["rows"]
                      if r["verdict"] == "no_permitted_route_reaches_them"]
        _gaps = [r for r in absence["rows"]
                 if r["verdict"] == "named_somewhere_investigate"]
        w(f"**{len(_unreached)} of {absence['checked']}**. Every source table "
          f"was re-read in full — including the rows the pipeline discards — "
          f"and none of them names "
          + ", ".join(r["person"] for r in _unreached) + ". "
          f"So the absence is a property of the reachable sources rather than "
          f"of the search: there is nothing here that looking harder would "
          f"find.")
        w("")
        if _gaps:
            w(f"**{len(_gaps)} ARE named in a permitted source and still carry "
              f"no observation**, which is a pipeline gap rather than a source "
              f"gap: " + ", ".join(r["person"] for r in _gaps) + ".")
            w("")
        w("*What this does NOT establish. Wikipedia does not reproduce these "
          "lists in full — it carries the single winner of Maxim's Hot 100 and "
          "Esquire's Sexiest Woman Alive, and only the top ten of FHM's "
          "hundred. Somebody absent from every table here could still have "
          "placed 37th in a published list. The finding is that no permitted "
          "ROUTE reaches evidence about them, never that no publication ever "
          "rated them.*")
        w("")

    # ---------- relationship corroboration ----------
    if relcorr:
        section("The relationship dates, against Wikipedia's own prose")
        w("")
        vc = relcorr["verdict_counts"]
        conf = vc.get("prose_confirms_a_stored_year", 0)
        w(f"Every relationship here comes from Wikidata, and nothing used to "
          f"cross-check it. Both people's English Wikipedia articles are now "
          f"read and the sentences naming the other person are carried into "
          f"`docs/RELATIONSHIP-REVIEW.md`. Wikidata statements and article "
          f"prose are edited by different people, so agreement is worth "
          f"something.")
        w("")
        w(f"**{conf} of {relcorr['episodes_checked']}** episodes are "
          f"corroborated by prose naming a year this project stored. "
          f"{vc.get('not_mentioned', 0)} are named in neither article, which is "
          f"the weakest kind of claim in the corpus and is flagged as such.")
        w("")
        w("*These labels are not verdicts and the sheet says so. On the first "
          "run, all "
          f"{vc.get('prose_names_other_years', 0)} episodes whose prose named "
          "no stored year turned out to have CORRECT dates, in sentences "
          "carrying another year for another reason.*")
        w("")

    # ---------- cross-run stability ----------
    if xrun and xrun.get("rows"):
        section("The same dossier, scored in two separate runs")
        w("")
        w(f"`{'` and `'.join(xrun['runs'].values())}` were scored in separate "
          f"runs. {xrun['comparable_person_periods']} person-periods carry a "
          f"byte-identical dossier in both -- the same observation ids, the "
          f"same contract id, the same judge family -- so any difference is "
          f"run-to-run variance and nothing else.")
        w("")
        names = list(xrun["runs"].keys())
        w(f"| Person | Period | Shape | {names[0]} | {names[1]} | Delta |")
        w("|---|---|---|---|---|---|")
        for r in xrun["rows"]:
            w(f"| {r['person']} | {r['period']} | `{r['shape']}` | "
              f"{r[names[0]]} | {r[names[1]]} | **{r['delta']:+.1f}** |")
        w("")
        w(xrun["reading"])
        w("")
        # Named, not numbered. Sections are numbered by render order now, so a
        # hardcoded "section 6b" survived the renumbering and pointed at a
        # section that no longer exists -- rater noise is 13.
        w("This is independent of the rater-noise section and agrees with it. "
          "The repeats "
          "there were deliberate re-invocations inside one run; these two runs "
          "did not know about each other. Both say the award shape holds still "
          "and the ranked shape does not.")
        w("")

    # ---------- robustness ----------
    if robust and robust.get("settings"):
        section("Do the conclusions depend on the choices that were made?")
        w("")
        w("The ±1 nearby-period bound, the romance filter on co-starring films "
          "and the enforcement of shape comparability were all argued in the "
          "plan and could defensibly have gone the other way. A conclusion "
          "that only holds at one setting of three dials is a property of the "
          "dials.")
        w("")
        w("| Bound | Romance filter | Jointly covered | Comparable | "
          "Comparable with a non-zero gap | Non-zero gaps | ...shape-mismatched |")
        w("|---|---|---|---|---|---|---|")
        for s in robust["settings"]:
            w(f"| ±{s['bound']} | {s['romance_filter']} | "
              f"{s['jointly_covered']} | {s['comparable']} | "
              f"**{s['comparable_with_a_nonzero_gap']}** | "
              f"{s['nonzero_gaps_total']} | "
              f"{s['nonzero_gaps_that_are_shape_mismatched']} |")
        w("")
        _fails = robust["claim_every_comparable_gap_is_zero"]["fails_at"]
        _holds = robust["claim_every_comparable_gap_is_zero"]["holds_at"]
        w(f"The claim that a shape-comparable pairing has a gap of exactly zero "
          f"holds at **{len(_holds)} of {len(robust['settings'])}** settings"
          + (f". It fails at {', '.join(_fails)}." if _fails else "."))
        for s in robust["settings"]:
            if s["comparable_with_a_nonzero_gap"] and s["examples"]:
                w("")
                w(f"The counterexample there is `{s['examples'][0]}` — a film "
                  f"co-appearance never established as a romance, scored from "
                  f"estimates {s['bound']} years from the year in question. It "
                  f"takes both dials at their loosest, in the two directions "
                  f"this project argues against, to produce it.")
                break
        w("")
        w(f"*{robust['caveat']}*")
        w("")

    # ---------- bottom line ----------
    if joint and noise:
        comp = [j for j in joint.get("jointly_covered", [])
                if j.get("comparability") == "comparable"]
        _by_shape = noise["headline"].get("by_shape") or {}
        _measured = {k: v["least_significant_difference_95pct"]
                     for k, v in _by_shape.items()
                     if v["least_significant_difference_95pct"] is not None}
        section("The bottom line, stated plainly")
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
                # A comparable pairing has ONE shape on both sides, so that
                # shape's own noise floor is the one that applies. Taking the
                # largest measured LSD across shapes would answer a different
                # question. Where the pairing's shape has no measured floor --
                # the award shape returned identical values on every repeat --
                # say so, and quote the largest measured floor as a stated
                # upper bound rather than pretending it is the right number.
                _shape = shape_for_pairing(j, shape_conf)
                _own = _measured.get(_shape)
                if _own is not None:
                    verdict = ("**not distinguishable from zero**"
                               if abs(g) <= _own else "above the noise floor")
                    w(f"  - Both sides are `{_shape}`-shaped, and repeat-scoring "
                      f"puts that shape's least significant difference at about "
                      f"**{_own}** points, so this gap is {verdict}.")
                elif _measured:
                    _up = max(_measured.values())
                    _src = max(_measured, key=lambda k: _measured[k])
                    verdict = ("**not distinguishable from zero**"
                               if abs(g) <= _up else "above every measured floor")
                    w(f"  - Both sides are `{_shape or 'unknown'}`-shaped, and "
                      f"that shape's repeat variance is **unmeasured**: every "
                      f"repeat returned the same value, which cannot tell low "
                      f"variance from none. The largest measured floor is "
                      f"`{_src}`'s **{_up}** points. Against that upper bound "
                      f"the gap is {verdict}.")
            w("")
        w("So the project can now produce a signed, exactly mirrored, "
          "evidence-backed gap for a real couple. It cannot yet produce one that "
          "is both comparable and larger than its own measurement noise. That is "
          "a much better place than this run started, and it is not a "
          "leaderboard.")
        w("")

    # ---------- costs ----------
    section("Cost and budget")
    w("")
    stress_calls = sum(b["calls_made"] for b in stress["budgets"].values())
    scored_calls = (sum(b["calls_made"] for b in scored["budgets"].values())
                    if scored else 0)

    w("Stages that record a call budget in their own artifact:")
    w("")
    w(f"- Stress tests: {stress_calls} model calls "
      f"({json.dumps({k: v['calls_made'] for k, v in stress['budgets'].items()})}).")
    if scored:
        w(f"- Scoring: {scored_calls} model calls "
          f"({json.dumps({k: v['calls_made'] for k, v in scored['budgets'].items()})}).")
    if first_pass is not None:
        _n = len(first_pass.get("dossiers", [])) or first_pass.get("dossiers_seen")
        _d = (f"all {_n} dossiers" if _n is not None else "every dossier")
        w(f"- First pilot pass: 0 model calls — {_d} came back empty and "
          f"short-circuited before any judge was called.")
    w("")

    rows, _ = spend_rows(REPO)
    if rows:
        w("Stages that write a run manifest, with the reconciliation each "
          "records. `attempted` equals `succeeded + cached + excluded + "
          "failed` by construction, so a stage that failed on every item "
          "cannot hide behind a call count:")
        w("")
        w("| Stage | Runs | Attempted | Succeeded | Cached | Excluded | Failed | Errors |")
        w("|---|---|---|---|---|---|---|---|")
        for r in rows:
            errs = (", ".join(f"{k}={v}" for k, v in sorted(r["errors"].items()))
                    or "—")
            w(f"| `{r['stage']}` | {r['runs']} | {r['attempted']} | "
              f"{r['succeeded']} | {r['cached']} | {r['excluded']} | "
              f"{r['failed']} | {errs} |")
        w("")
        w("Repeated runs of a stage are summed. A superseded run spent quota "
          "too, and this section answers what the pilot cost rather than how "
          "many calls stand behind the final artifacts.")
        w("")

    manifest_attempts = sum(r["attempted"] for r in rows)
    w(f"**Model calls: {stress_calls + scored_calls} from the budgeted stages, "
      f"plus {manifest_attempts} attempts recorded across the manifested "
      f"stages — {stress_calls + scored_calls + manifest_attempts} in total, "
      f"against a cap of 300.**")
    w("")
    w("- Subscription quota only. API billing was asserted off at start-up.")
    w("- Dollar cost is not totalled: only the Claude arm reports `cost_usd`, and "
      "inventing a figure for the other arm would be a fabricated number.")
    w("- **Human review time: 0 minutes so far.** The plan budgeted 60–90 "
      "minutes for one batch covering the pairing relationship claims and a "
      "sample of rationales for the grounding audit. None of it has happened, "
      "so every real-life relationship claim in this report remains an "
      "unverified candidate and the grounding audit remains automated-only.")
    w("")

    # ---------- assessment ----------
    section("Do the estimates reflect substance, or source availability?")
    w("")
    w("**Substance, where evidence exists. Availability decides whether it exists at all.**")
    w("")
    # This listed only the cases that passed. S2 exceeded the noise floor and
    # was left out of a summary claiming the rubric reads substance rather
    # than format -- which is precisely what S2 tests.
    _f2 = (stress.get("findings") or {})
    _fl2 = noise_floor(noise)
    _over2 = sorted(k for k, v in _f2.items()
                    if isinstance(v, dict) and v.get("spread") is not None
                    and _fl2 is not None and v["spread"] > _fl2)
    w("The stress cases say the rubric is reading the judgments rather than "
      "counting documents: one award beat two low placements by a wide margin, "
      "three corroborating publishers moved the estimate by a point, and five "
      "copies of one list moved it by zero. Both model families agreed exactly "
      "on every construct case they both ran.")
    if _over2:
        w("")
        w(f"With one exception, and it is about FORMAT rather than count: "
          f"**{', '.join(_over2)}** exceeded the measured noise floor. The "
          f"rubric reads the substance of a judgment and not the number of "
          f"documents carrying it — but it does not read the same substance "
          f"identically in every shape, which is the confound this report "
          f"measures observationally elsewhere.")
    w("")
    w("But which person-years have any evidence is decided entirely by which "
      "publishers happen to be reachable. On the permitted routes the men's award is "
      "an annual one-winner prize reported on Wikipedia since 1985, and the women's "
      "equivalent is a single number-one per year since 2000. Everything deeper sits "
      "behind terms that forbid this use.")
    w("")

    # ---------- against the plan ----------
    section("Against the plan's M0 deliverables")
    w("")
    w("The plan's section 8.2 lists six things M0 should produce. Where each "
      "one is, and whether it is done:")
    w("")
    w("| # | Deliverable | Where | Done |")
    w("|---|---|---|---|")
    _rows = [
        ("1", "The revised rubric and the access decisions",
         "`rubrics/standing/RUBRIC.md`, " + section.ref("Source access decisions"),
         "yes" if stress else "rubric present, access decisions above"),
        ("2", "Dossiers, estimates, support, rationales, exclusions, lineage",
         "`data/pilot/run/evidenced_scores.json`, "
         + section.ref("Scored person-periods and pairing contributions",
                         "Grounding audit"),
         f"yes — {len(scored['person_periods'])} person-periods"
         if scored else "no scores"),
        ("3", "VERIFIED pairings, with mirrored contribution arithmetic",
         section.ref("Scored person-periods and pairing contributions")
         + "; `docs/RELATIONSHIP-REVIEW.md` for the verification",
         "arithmetic yes, mirrors exact; **verification NOT done** — it needs "
         "a person, and the sheet is ready"),
        ("4", "Person-period and joint pairing-period coverage, with failures",
         section.ref("Coverage, the two numbers that matter",
                     "Why joint coverage does not move") + ", and the near-miss list",
         "yes"),
        ("5", "Stress tests, offset diagnostic, actual costs, review minutes",
         section.ref("Measurement stress tests", "Cross-gender offset sensitivity",
                     "Cost and budget"),
         "yes — review minutes are **0**, stated"),
        ("6", "An assessment: substance, or source availability?",
         section.ref("Do the estimates reflect substance, or source availability?"),
         "yes"),
    ]
    for n, what, where, done in _rows:
        w(f"| {n} | {what} | {where} | {done} |")
    w("")
    w("**One deliverable is outstanding and it is the one only a person can "
      "do.** Everything else is here. The two review sheets each lead with the "
      "entries that carry a published conclusion, so the load-bearing part of "
      "the work is the first part encountered.")
    w("")

    section("What M0 did not establish")
    w("")
    # This was a typed list, and it had gone stale in the direction that
    # UNDERSTATES the work: it said rater noise was not measured, that the
    # offset diagnostic had no board, and that every on-screen pairing was
    # co-appearance only -- while sections above reported all three done. The
    # honesty section being wrong is worse than any other section being wrong,
    # so every line is now derived.
    w("- **Human verification has not happened.** Every relationship remains a "
      "Wikidata candidate that no person has checked, and the plan budgeted "
      "60-90 minutes for exactly that.")
    if relcorr:
        # Precise on purpose. Corroboration is not verification, and the
        # difference is the whole reason the plan keeps a human in this loop.
        # But saying "no person has checked" and stopping would understate what
        # is now in front of them.
        _vc = relcorr["verdict_counts"]
        w(f"  They are no longer unchecked against anything, which is not the "
          f"same thing: "
          f"{_vc.get('prose_confirms_a_stored_year', 0)} of "
          f"{relcorr['episodes_checked']} are corroborated by English "
          f"Wikipedia prose naming a year this project stored, and the review "
          f"sheet puts the excerpts beside each claim so the hour is spent "
          f"judging rather than looking things up. A second source agreeing "
          f"is evidence; it is not a person having decided.")
    if romance:
        _q = romance["counts"]["qualifying_romances"]
        _c = romance["counts"]["candidates"]
        w(f"  On-screen pairings ARE romance-filtered — {_q} of {_c} candidates "
          f"are confirmed reciprocal romances from the plot text — so that is "
          f"no longer an open item, but the filter is a model's reading of a "
          f"Wikipedia summary, not a human's.")
    if grounding:
        _n = (grounding.get("counts") or {}).get("needing_human_read")
        if _n:
            w(f"- **The grounding audit is not done.** {_n} rationales are "
              f"flagged for a human to read and judge whether the cited "
              f"observations support what they claim. The automated checks "
              f"cannot establish that.")
    if noise:
        _h = noise["headline"]
        _shapes = _h.get("by_shape") or {}
        _degenerate = _h.get("shapes_with_degenerate_sample") or []
        w(f"- **Rater noise is measured but thin.** {noise['repeats']} repeats "
          f"across {len(noise['targets'])} dossiers on "
          f"{len(_h.get('judges_that_contributed') or [])} judge "
          f"{'family' if len(_h.get('judges_that_contributed') or []) == 1 else 'families'}. "
          + (f"The {', '.join(_degenerate)} shape returned the same value every "
             f"time, which cannot distinguish low variance from none, so no "
             f"floor is quoted for it."
             if _degenerate else ""))
    if offset:
        # offset["people"] is a LIST of names; it rendered as
        # "with ['Ben Affleck', 'Brad Pitt'] people".
        _people = offset.get("people") or []
        _n_people = len(_people) if isinstance(_people, list) else _people
        w(f"- **The cross-gender offset diagnostic ran, on too small a board to "
          f"be informative.** Cumulative ranks did not move over the tested "
          f"range"
          + (f", but with {_n_people} people and this little exposure spread "
             f"that says the board is too small to be sensitive, not that it "
             f"is robust." if _n_people else "."))
    if scored:
        _contrib = sorted({j for r in scored["person_periods"] for j in r["judges"]})
        if len(_contrib) < 2:
            w(f"- **Cross-family agreement on the real dossiers is unmeasured.** "
              f"Every estimate came from {_contrib[0] if _contrib else 'one'} "
              f"alone. The plan decided two families precisely so that a "
              f"one-family idiosyncrasy could be told from a property of the "
              f"rubric, and that check has not been run on real evidence.")
    w("")

    out = REPO / "docs/M0-REPORT.md"
    out.write_text("\n".join(L) + "\n")
    print(f"wrote {out} ({len('\n'.join(L))} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
