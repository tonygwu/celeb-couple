"""A function nothing calls is not a capability; it is a plan for one.

This project has now shipped the same defect twice. `refuse_mixed_contracts`
was written to stop scores from different rubrics being pooled and had no
production caller for weeks. `Budget.spend_fetch` backs the plan's "HTTP
fetches <= 200, paced, breaker armed" and is called by nothing, so every run
artifact published a cap of 10**9 beside a count that was structurally zero.

Both were found by looking, not by any check. This is the check.

It is not a demand that everything be called. Plenty here is legitimately
written ahead of use: M0 publishes no board, so the ranking gate and the
Partner_WAR baseline have nothing to run against yet. What the allowlist buys
is that each of those is a DECISION somebody wrote down, rather than an
oversight nobody noticed. A new uncalled function fails until it is either
wired up or explained here.
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Public functions with no caller in modules/, packages/ or scripts/, and why
#: that is currently correct. Tests calling them is not "called": a test can
#: only show a function works, never that anything uses it.
KNOWN_UNCALLED = {
    # --- post-M0 by design. The plan stops before a published board. -------
    "qualify": "plan 3.6, who may carry a rank; M0 publishes no ranks",
    "with_baseline": "plan 3.7 Partner_WAR baseline; frozen in the metric release, after M0",
    "cohort_median_partner": "the descriptive statistic shown beside that baseline",
    "count_like_diagnostic": "plan 4's count-like diagnostic; reports against a board M0 has not built",
    "gap_years": "plan example E's exact-arithmetic metric; no cumulative PAW in M0",
    "same_shape_view": "the same-shape board view; M0 reports comparability instead",
    # --- kept deliberately, with the reason -------------------------------
    "refuse_mixed_contracts": (
        "no production caller and that is correct: nothing here pools two "
        "scored artifacts, and cross_run_stability.py refuses by hand with a "
        "better message. See docs/BACKLOG.md"),
    "spend_fetch": (
        "the plan's fetch cap is enforced nowhere; wiring it is a decision "
        "about how much of Wikipedia to pull in one run. See docs/BACKLOG.md"),
    # --- thin wrappers whose callers use the fuller form -------------------
    "merge_progressions": "convenience wrapper; production calls merge_progressions_with_stats",
    "parse_award_table": "convenience wrapper; production calls parse_award_table_with_stats",
    # --- small helpers on public types ------------------------------------
    "is_exact": "PreciseDate helper, used by callers of the temporal package",
    "year_days": "leap-year day count; the exact-arithmetic path that needs it is post-M0",
    "level": "a record's public accessor",
    "classify_detail": "failure-taxonomy detail, carried in artifacts rather than branched on",
}


def _files(bases):
    for b in bases:
        for p in sorted((REPO / b).rglob("*.py")):
            if "__pycache__" not in str(p):
                yield p


def uncalled_public_functions() -> dict[str, str]:
    """Public functions in modules/ and packages/ that nothing references.

    References are collected from the AST, so a name appearing only in a
    comment or a docstring does not count as a use -- which is the whole point,
    since both of the real defects were discussed in prose while being called
    by nothing.
    """
    defs: dict[str, str] = {}
    for p in _files(("modules", "packages")):
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and not node.name.startswith("_"):
                defs.setdefault(node.name, str(p.relative_to(REPO)))
    refs: set[str] = set()
    for p in _files(("modules", "packages", "scripts")):
        for node in ast.walk(ast.parse(p.read_text())):
            if isinstance(node, ast.Name):
                refs.add(node.id)
            elif isinstance(node, ast.Attribute):
                refs.add(node.attr)
    return {n: f for n, f in defs.items() if n not in refs}


def test_no_unexplained_uncalled_function():
    found = uncalled_public_functions()
    new = {n: f for n, f in found.items() if n not in KNOWN_UNCALLED}
    assert new == {}, (
        "these public functions are called by nothing in modules/, packages/ "
        "or scripts/. Wire them up, or add them to KNOWN_UNCALLED with the "
        "reason that is correct:\n  "
        + "\n  ".join(f"{n}  ({f})" for n, f in sorted(new.items()))
    )


def test_the_allowlist_has_no_stale_entries():
    """An entry that has since gained a caller is a comment that has gone
    false, and this file would then be documenting the opposite of the truth."""
    found = uncalled_public_functions()
    stale = sorted(set(KNOWN_UNCALLED) - set(found))
    assert stale == [], (
        "these are listed as uncalled but now have callers; remove them from "
        f"KNOWN_UNCALLED: {stale}")


def test_every_entry_carries_a_reason():
    empty = sorted(n for n, why in KNOWN_UNCALLED.items() if len(why) < 20)
    assert empty == [], f"allowlist entries without a real reason: {empty}"


def test_the_analysis_finds_a_function_nothing_calls():
    """A detector that returns nothing would pass this file silently."""
    found = uncalled_public_functions()
    assert "spend_fetch" in found, (
        "spend_fetch has no caller; if the detector cannot see that, it cannot "
        "see the next one either")
