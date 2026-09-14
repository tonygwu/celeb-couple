"""The generated report must DERIVE its prose claims, not assert them.

Measured 2026-09-14: after the Wikidata-label fix grew the corpus from 34 to 39
person-periods, `docs/M0-REPORT.md` still said "Every scored person-period
carries exactly one observation, and every one of those observations is a
one-winner editorial award." Both halves were false. Two person-periods carried
two observations, and the corpus held 17 ordered ranks and 4 unordered
inclusions alongside the 20 awards.

The generator's header promises "Every number below is read from a JSON
artifact, not typed." That promise covered the numbers and not the sentences
around them, which is the same defect wearing a different hat: a claim nobody
recomputed when the inputs moved.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _gen():
    spec = importlib.util.spec_from_file_location(
        "write_m0_report", REPO / "scripts/write_m0_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MIXED = {
    "by_shape": {
        "editorial_award": {"n": 18, "mean": 91.28, "min": 78.0, "max": 94.0,
                            "sd": 3.263},
        "ordered_rank": {"n": 16, "mean": 84.56, "min": 64.0, "max": 93.0,
                         "sd": 6.727},
        "unordered_inclusion": {"n": 3, "mean": 80.67, "min": 76.0, "max": 86.0,
                                "sd": 4.11},
    }
}
MIXED_DENSITY = {"distribution": {"1": 37, "2": 2}, "person_periods": 39}

SINGLE = {"by_shape": {"editorial_award": {"n": 12, "mean": 92.0, "min": 92.0,
                                           "max": 92.0, "sd": 0.0}}}
SINGLE_DENSITY = {"distribution": {"1": 12}, "person_periods": 12}


def test_it_does_not_claim_a_single_shape_when_the_corpus_holds_three():
    text = _gen().shape_paragraph(MIXED, MIXED_DENSITY)
    low = text.lower()
    assert "every one of those observations" not in low
    assert "exactly one observation" not in low, (
        "two person-periods carry two observations in this fixture"
    )
    for shape in ("editorial_award", "ordered_rank", "unordered_inclusion"):
        assert shape in text, f"{shape} is in the corpus and must be named"


def test_it_reports_the_real_counts_and_spreads():
    text = _gen().shape_paragraph(MIXED, MIXED_DENSITY)
    for n in ("18", "16", "3", "78.0", "94.0", "64.0", "93.0"):
        assert n in text, f"{n} comes straight from by_shape and must appear"


def test_a_genuinely_uniform_corpus_is_still_described_as_uniform():
    """The old sentence was not wrong when it was written. It stopped being
    true. A corpus that really does hold one shape must still say so."""
    text = _gen().shape_paragraph(SINGLE, SINGLE_DENSITY)
    assert "editorial_award" in text
    assert "ordered_rank" not in text


def test_it_says_how_many_person_periods_carry_more_than_one_observation():
    assert "2 of 39" in _gen().shape_paragraph(MIXED, MIXED_DENSITY)
    assert "every" in _gen().shape_paragraph(SINGLE, SINGLE_DENSITY).lower()


def test_the_committed_report_matches_the_committed_artifacts():
    """Optional: only runs in a clone that has produced the artifacts."""
    import json
    conf = REPO / "data/pilot/run/shape_confound.json"
    dens = REPO / "data/pilot/run/evidence_density.json"
    if not (conf.exists() and dens.exists()):
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")
    para = _gen().shape_paragraph(json.loads(conf.read_text()),
                                  json.loads(dens.read_text()))
    report = (REPO / "docs/M0-REPORT.md").read_text()
    assert para in report, "docs/M0-REPORT.md is stale; re-run write_m0_report.py"


# --------------------------------------------------------------------------
# The report's input fingerprint
# --------------------------------------------------------------------------

def test_the_fingerprint_ignores_a_changed_generation_timestamp():
    """Measured 2026-09-14: `bash scripts/run_chain.sh reports` produced a
    one-line diff in docs/M0-REPORT.md -- the fingerprint -- with not one
    number moved. Ten artifacts carry `generated_at_utc`, the fingerprint
    hashed the raw bytes, and so it tracked when the chain last ran rather
    than what the chain found.

    That is the defect the fingerprint was introduced to fix. verbatim-index
    stamped its pages with the RENDER date, which made every regeneration a
    diff and told a reader nothing. Hashing a generation timestamp inside the
    inputs is the same bug one level down.
    """
    gen = _gen()
    a = {"generated_at_utc": "2026-09-14T10:00:00+00:00", "n": 39}
    b = {"generated_at_utc": "2026-09-14T23:59:59+00:00", "n": 39}
    assert gen.stable_bytes(a) == gen.stable_bytes(b)


def test_the_fingerprint_still_moves_when_a_number_moves():
    gen = _gen()
    a = {"generated_at_utc": "2026-09-14T10:00:00+00:00", "n": 39}
    c = {"generated_at_utc": "2026-09-14T10:00:00+00:00", "n": 40}
    assert gen.stable_bytes(a) != gen.stable_bytes(c)


def test_a_nested_generation_timestamp_is_also_ignored():
    gen = _gen()
    a = {"run": {"generated_at_utc": "2026-09-14T10:00:00+00:00", "n": 1}}
    b = {"run": {"generated_at_utc": "2026-09-15T10:00:00+00:00", "n": 1}}
    assert gen.stable_bytes(a) == gen.stable_bytes(b)


def test_a_meaningful_date_is_never_stripped():
    """`data_as_of` and `last_supported_active` are findings, not stamps. An
    over-broad strip would hide a real change in the evidence cutoff."""
    gen = _gen()
    a = {"data_as_of": "2026-09-14", "last_supported_active": "2005-01-01"}
    b = {"data_as_of": "2026-09-20", "last_supported_active": "2005-01-01"}
    assert gen.stable_bytes(a) != gen.stable_bytes(b)
    c = {"data_as_of": "2026-09-14", "last_supported_active": "2006-01-01"}
    assert gen.stable_bytes(a) != gen.stable_bytes(c)


def test_a_non_json_input_is_still_hashed():
    gen = _gen()
    assert gen.stable_bytes(b"raw bytes") == b"raw bytes"


# --------------------------------------------------------------------------
# Section numbering
# --------------------------------------------------------------------------

def test_sections_are_numbered_by_render_order():
    """The numbers were typed into each heading, and after sections were added,
    reordered and made conditional the report shipped TWO section 6s and ran
    6, 6, 6e, 5, 5b, 6f, 6a, 6b, 6c, 6d, 6c-bis, 6g. A reader could not use
    them to navigate."""
    gen = _gen()
    out = []
    s = gen.Sections(out.append)
    s.unnumbered("The answer first")
    s("Cohort")
    s("Records")
    assert out == ["## The answer first", "## 1. Cohort", "## 2. Records"]


def test_a_skipped_conditional_section_does_not_leave_a_gap():
    """Whether a section renders depends on which artifacts exist. Typed
    numbers left a hole; counted ones cannot."""
    gen = _gen()
    out = []
    s = gen.Sections(out.append)
    s("A")
    # ...the section that would have been 2 has no artifact and is skipped...
    s("C")
    assert out == ["## 1. A", "## 2. C"]


def test_the_committed_report_has_no_duplicate_or_out_of_order_sections():
    """Optional: reads the committed report itself."""
    import re
    text = (REPO / "docs/M0-REPORT.md").read_text()
    nums = [int(m) for m in re.findall(r"^## (\d+)\. ", text, re.M)]
    assert nums == sorted(nums), f"sections out of order: {nums}"
    assert len(nums) == len(set(nums)), f"duplicate section numbers: {nums}"
    assert nums == list(range(1, len(nums) + 1)), f"gap in numbering: {nums}"


# --------------------------------------------------------------------------
# Which noise floor applies to a comparable pairing
# --------------------------------------------------------------------------

SHAPES = {"rows": [
    {"person": "A", "period": "2003", "estimate": 92.0, "shape": "editorial_award"},
    {"person": "B", "period": "2003", "estimate": 92.0, "shape": "editorial_award"},
    {"person": "C", "period": "1999", "estimate": 92.0, "shape": "editorial_award"},
    {"person": "D", "period": "1999", "estimate": 86.0, "shape": "ordered_rank"},
]}


def test_a_comparable_pairing_reports_its_own_shape():
    """A comparable pairing has one shape on both sides, so that shape's floor
    is the one that applies. The code took max() across shapes while its own
    comment said it used the pairing's shape."""
    gen = _gen()
    got = gen.shape_for_pairing(
        {"a": "A", "b": "B", "period": "2003"}, SHAPES)
    assert got == "editorial_award"


def test_a_mismatched_pairing_has_no_single_shape():
    gen = _gen()
    assert gen.shape_for_pairing(
        {"a": "C", "b": "D", "period": "1999"}, SHAPES) is None


def test_a_nearby_reused_estimate_still_resolves_its_shape():
    gen = _gen()
    rows = {"rows": [
        {"person": "A", "period": "2000", "estimate": 92.0, "shape": "editorial_award"},
        {"person": "B", "period": "2000", "estimate": 92.0, "shape": "editorial_award"}]}
    got = gen.shape_for_pairing(
        {"a": "A", "b": "B", "period": "2001", "a_src": "2000", "b_src": "2000"},
        rows)
    assert got == "editorial_award", "reuse must not lose the shape"


def test_an_unknown_person_yields_no_shape_rather_than_a_wrong_one():
    gen = _gen()
    assert gen.shape_for_pairing(
        {"a": "A", "b": "NOBODY", "period": "2003"}, SHAPES) is None


def test_the_report_says_the_award_floor_is_unmeasured():
    """The one comparable pairing is award+award, and the award shape returned
    identical values on every repeat. Quoting the ranked floor as though it
    were this pairing's would overstate what was measured."""
    text = (REPO / "docs/M0-REPORT.md").read_text()
    if "The bottom line" not in text:
        pytest.skip("report not generated in this clone")
    assert "repeat variance is **unmeasured**" in text
    assert "upper bound" in text


# --------------------------------------------------------------------------
# Per-stage spend aggregation
# --------------------------------------------------------------------------

def test_a_single_run_is_not_counted_twice(tmp_path):
    """`merged.setdefault(stage, dict(r, runs=0))` seeded the accumulator with
    the FIRST row's values and then added that row again. Every stage came out
    inflated by exactly its first run:

        prose-mentions  manifest 14  ->  report 28
        rater-noise     manifest 58  ->  report 74
        romance         manifest 60  ->  report 80

    I introduced this while fixing a cost section that UNDER-reported spend.
    Replacing an undercount with an overcount is not a fix, and the headline
    "248 model calls against a cap of 300" was wrong in the other direction.
    """
    import json
    gen = _gen()
    d = tmp_path / "data/pilot/manifests"
    d.mkdir(parents=True)
    (d / "r1.json").write_text(json.dumps({
        "stage_name": "extract",
        "summaries": [{"attempted": 14, "succeeded": 14, "cached": 0,
                       "excluded": 0, "failed": 0, "error_taxonomy": {}}]}))
    rows, _ = gen.spend_rows(tmp_path)
    assert len(rows) == 1
    assert rows[0]["attempted"] == 14, rows[0]
    assert rows[0]["runs"] == 1


def test_repeated_runs_of_a_stage_are_summed_once_each(tmp_path):
    import json
    gen = _gen()
    d = tmp_path / "data/pilot/manifests"
    d.mkdir(parents=True)
    for i, n in enumerate((16, 8, 2)):
        (d / f"r{i}.json").write_text(json.dumps({
            "stage_name": "repeat-score",
            "summaries": [{"attempted": n, "succeeded": n, "cached": 0,
                           "excluded": 0, "failed": 0, "error_taxonomy": {}}]}))
    rows, _ = gen.spend_rows(tmp_path)
    assert rows[0]["runs"] == 3
    assert rows[0]["attempted"] == 26


def test_error_taxonomies_are_merged_without_doubling(tmp_path):
    import json
    gen = _gen()
    d = tmp_path / "data/pilot/manifests"
    d.mkdir(parents=True)
    (d / "r1.json").write_text(json.dumps({
        "stage_name": "repeat-score",
        "summaries": [{"attempted": 8, "succeeded": 0, "cached": 0,
                       "excluded": 0, "failed": 8,
                       "error_taxonomy": {"auth_or_quota": 8}}]}))
    rows, _ = gen.spend_rows(tmp_path)
    assert rows[0]["errors"] == {"auth_or_quota": 8}


def test_a_half_written_manifest_is_not_counted_as_spend(tmp_path):
    """A .tmp or truncated file is a failed write, not a run."""
    import json
    gen = _gen()
    d = tmp_path / "data/pilot/manifests"
    d.mkdir(parents=True)
    (d / "good.json").write_text(json.dumps({
        "stage_name": "extract",
        "summaries": [{"attempted": 3, "succeeded": 3, "cached": 0,
                       "excluded": 0, "failed": 0, "error_taxonomy": {}}]}))
    (d / "broken.json").write_text("")
    rows, _ = gen.spend_rows(tmp_path)
    assert len(rows) == 1 and rows[0]["attempted"] == 3


# --------------------------------------------------------------------------
# The identity-leakage row
# --------------------------------------------------------------------------

NOISE = {"headline": {"by_shape": {
    "ranked": {"least_significant_difference_95pct": 2.22},
    "award": {"least_significant_difference_95pct": None}}}}


def test_a_spread_below_the_noise_floor_is_not_leakage():
    """The report printed the artifact's stored reading verbatim -- "identity
    moved the score" -- while the arms behind it read named 82, anonymised
    82.5, swapped 82. A spread of 0.5 is below every noise floor this project
    has measured.

    It told the operator the rubric leaks identity, in a document whose
    conclusion is that the measurement works, on a sentence nobody recomputed.
    """
    gen = _gen()
    row = gen.identity_leakage_row(
        {"per_arm": {"named": 82, "anonymised": 82.5, "swapped_name": 82},
         "reading": "identity moved the score"}, NOISE)
    assert "did NOT move the score" in row
    assert "identity moved the score" not in row, (
        "the stored string must not be repeated; it is what was wrong"
    )


def test_a_spread_above_the_noise_floor_is_flagged():
    gen = _gen()
    row = gen.identity_leakage_row(
        {"per_arm": {"named": 70, "anonymised": 90}}, NOISE)
    assert "possible leakage" in row


def test_the_newer_per_judge_shape_is_handled():
    """run_stress.py now reports per judge; the artifact on disk predates that,
    which is how `per_judge` rendered as null."""
    gen = _gen()
    row = gen.identity_leakage_row(
        {"per_judge": {"fable": {"named": 82, "anonymised": 82}}}, NOISE)
    assert "did NOT move the score" in row


def test_a_missing_artifact_says_so_rather_than_concluding():
    gen = _gen()
    assert "re-run" in gen.identity_leakage_row({}, NOISE)


def test_no_noise_floor_means_no_verdict():
    """Without a measured floor, a spread is not evidence either way. Saying so
    beats picking a direction."""
    gen = _gen()
    row = gen.identity_leakage_row(
        {"per_arm": {"named": 82, "anonymised": 82.5}}, None)
    assert "not yet evidence either way" in row


def test_a_spread_above_the_floor_is_not_called_comparable():
    """S2 renders the SAME judgment as an award, a rank and prose. It recorded
    a 4-point spread and the stored reading called it "formats scored
    comparably" -- but 4 exceeds the measured 2.22, so it is the opposite: a
    format effect on identical substance, which is the evidence-shape confound
    under controlled conditions. It was being reported as a pass."""
    gen = _gen()
    v = gen.spread_verdict(4, 2.22, "comparable", "format moved the estimate")
    assert "ABOVE" in v and "format moved the estimate" in v


def test_a_spread_within_the_floor_reads_as_no_effect():
    gen = _gen()
    v = gen.spread_verdict(1, 2.22, "left the estimate where it was", "moved it")
    assert "within" in v and "left the estimate where it was" in v


def test_a_spread_exactly_at_the_floor_is_within_it():
    gen = _gen()
    assert "within" in gen.spread_verdict(2.22, 2.22, "no effect", "effect")


def test_no_floor_means_no_verdict_for_any_case():
    gen = _gen()
    assert "not yet evidence" in gen.spread_verdict(4, None, "a", "b")


def test_a_missing_spread_says_so():
    gen = _gen()
    assert gen.spread_verdict(None, 2.22, "a", "b") == "no spread recorded"


def test_the_floor_comes_from_a_measured_shape_only():
    """The award shape has no LSD -- every repeat returned the same value --
    and a None must not be picked up as a floor of zero, which would make every
    spread look significant."""
    gen = _gen()
    assert gen.noise_floor(NOISE) == 2.22
    assert gen.noise_floor({"headline": {"by_shape": {
        "award": {"least_significant_difference_95pct": None}}}}) is None
    assert gen.noise_floor(None) is None


def test_the_reuse_sentence_counts_rather_than_saying_both():
    """It said the literal word "Both", written when there were two jointly
    covered pairings. There are now four, and one is contemporaneous on both
    sides, so "Both are reused estimates" was false of half the list."""
    import re
    text = (REPO / "docs/M0-REPORT.md").read_text()
    if "bounded reuse" not in text:
        pytest.skip("report not generated in this clone")
    assert "Both are reused estimates" not in text
    m = re.search(r"(\d+) of (\d+) rest on at least one estimate reused", text)
    assert m, "the reuse count must be derived and stated"
    used, total = int(m.group(1)), int(m.group(2))
    assert used <= total


def test_the_near_misses_are_listed_not_narrated():
    """The section carried a typed sentence naming Affleck and Garner and "four
    pairings together". Which pairings have exactly one side evidenced is a
    property of the corpus and moves whenever the corpus does."""
    text = (REPO / "docs/M0-REPORT.md").read_text()
    if "near-misses" not in text:
        pytest.skip("report not generated in this clone")
    assert "each have 2002 evidence and four pairings together" not in text
    assert "has none in range" in text, (
        "each near-miss must name which side is missing"
    )


def test_the_opening_does_not_claim_every_construct_check_passed():
    """It was typed, and S2's 4-point format spread is above the measured
    floor, so it does not pass. A summary that asserts a clean sweep while the
    table three screens down shows a failure is the worst place to be wrong."""
    text = (REPO / "docs/M0-REPORT.md").read_text()
    if "The answer first" not in text:
        pytest.skip("report not generated in this clone")
    assert "every construct check passed" not in text


def test_the_opening_scopes_the_two_family_claim():
    """"Two model families independently agreed" is true of the STRESS corpus
    and false of the real dossiers, where one family scored everything. Left
    unscoped it reads as cross-validation of the estimates."""
    text = (REPO / "docs/M0-REPORT.md").read_text()
    if "The answer first" not in text:
        pytest.skip("report not generated in this clone")
    assert "did not both run on the real dossiers" in text


def test_the_scores_section_says_how_many_judges_produced_them():
    text = (REPO / "docs/M0-REPORT.md").read_text()
    if "Scored person-periods" not in text:
        pytest.skip("report not generated in this clone")
    assert "rests on ONE judge" in text or "judge gap" not in text
