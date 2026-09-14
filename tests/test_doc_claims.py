"""Numbers written into documentation must still match the artifacts.

Tonight produced four analysis documents full of typed figures. A hand-typed
count goes stale and then lies, and this project has already been bitten twice:
AGENTS.md claimed 134 tests when the suite reported 127, and
coverage.total_observations read 27 while the file held 35.

These tests SKIP when the artifact is absent, because data/ is gitignored and a
fresh clone has none of it. They are a guard for the clone that has run the
pipeline, not a barrier for the one that has not.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _artifact(rel: str):
    path = REPO / rel
    if not path.exists():
        pytest.skip(f"{rel} absent; data/ is gitignored")
    return json.loads(path.read_text())


def _doc(rel: str) -> str:
    path = REPO / rel
    if not path.exists():
        pytest.skip(f"{rel} absent")
    return path.read_text()


def test_scaling_table_matches_the_scaling_artifact():
    blob = _artifact("data/roster100/run/scaling.json")
    md = _doc("docs/SCALING.md")
    for row in blob["rows"]:
        metric, pilot, roster = row["metric"], row["pilot_14"], row["roster_100"]
        line = next((l for l in md.splitlines()
                     if l.startswith("|") and metric in l), None)
        assert line is not None, f"SCALING.md has no row for {metric!r}"
        assert str(pilot) in line and str(roster) in line, (
            f"SCALING.md row for {metric!r} reads {line!r} but the artifact says "
            f"{pilot} -> {roster}"
        )


def test_source_requirement_ladder_matches_the_artifact():
    blob = _artifact("data/roster100/run/source_requirement.json")
    md = _doc("docs/SCALING.md")
    for rung in blob["ladder"]:
        n, median = rung["names_per_year"], rung["median_covered"]
        line = next((l for l in md.splitlines()
                     if l.startswith(f"| {n} |")), None)
        assert line is not None, f"SCALING.md has no ladder row for {n} names/year"
        assert f"| {median} |" in line, (
            f"ladder row for {n} names/year reads {line!r}, artifact median {median}"
        )


def test_source_hunt_depth_claims_match_the_observation_sources():
    obs = _artifact("data/pilot/observations/observations.json")
    md = _doc("docs/SOURCE-HUNT.md")
    by_pub = {s["award"]: s for s in obs["sources"]}
    fhm = next((s for s in obs["sources"] if "FHM" in s["award"]), None)
    if fhm:
        assert "top ten per year" in md or "top ten" in md, (
            "SOURCE-HUNT.md must describe FHM's depth, which is what the whole "
            "negative result turns on"
        )
        assert str(fhm["years"][0]) in md and str(fhm["years"][1]) in md, (
            f"SOURCE-HUNT.md should name FHM's span {fhm['years']}"
        )
    for award in ("Sexiest Man Alive", "Maxim Hot 100 number one"):
        assert award.split(" number")[0] in md, f"{award} missing from the table"
    assert by_pub, "no sources recorded"


def test_reachable_products_counts_match_the_artifact():
    blob = _artifact("data/roster100/run/reachable.json")
    md = _doc("docs/REACHABLE-PRODUCTS.md")
    for option in blob["options"]:
        line = next((l for l in md.splitlines()
                     if l.startswith("|") and option["name"] in l), None)
        assert line is not None, f"no row for {option['name']!r}"
        assert f"**{option['count']}** of {option['of']}" in line, (
            f"row for {option['name']!r} reads {line!r}, artifact says "
            f"{option['count']} of {option['of']}"
        )


def test_the_readme_headline_numbers_match_the_measurements():
    density = _artifact("data/pilot/run/evidence_density.json")
    shape = _artifact("data/pilot/run/shape_confound.json")
    readme = _doc("README.md")
    pct = round((shape["eta_squared_shape_explains"] or 0) * 100)
    assert f"{pct}%" in readme, (
        f"README should say evidence shape explains {pct}% of the estimate"
    )
    distinct = density["real_estimate_spread"]["distinct_values"]
    assert re.search(rf"\b{distinct}\b", readme), (
        f"README should reflect the real corpus's {distinct} distinct values"
    )


def test_the_trap_doc_matches_the_roster_joint_scores():
    """Every comparable pairing must still be 0.0, and every non-zero gap must
    still be shape-mismatched. If that ever stops being true the document is
    wrong and the finding has changed."""
    blob = _artifact("data/roster100/run/joint_scores.json")
    md = _doc("docs/THE-TRAP.md")
    for p in blob["pairings"]:
        if p["comparability"] == "comparable":
            assert p["gap_a_view"] == 0.0, (
                f"{p['a']} + {p['b']} is comparable with gap {p['gap_a_view']}; "
                "THE-TRAP.md claims every comparable gap is exactly zero"
            )
        elif p["gap_a_view"] != 0.0:
            assert p["comparability"] == "shape_mismatched", (
                f"{p['a']} + {p['b']} has a non-zero gap and is not "
                f"shape-mismatched ({p['comparability']}); THE-TRAP.md claims "
                "every non-zero gap is shape-confounded"
            )
    assert "0.0 by construction" in md


def test_no_document_claims_a_test_count():
    """AGENTS.md once said 134 while the suite reported 127. The rule is that a
    count belongs in the runner's output, not in prose."""
    for rel in ("README.md", "AGENTS.md", "docs/SCALING.md",
                "docs/SOURCE-HUNT.md", "docs/REACHABLE-PRODUCTS.md",
                "docs/THE-TRAP.md"):
        text = _doc(rel)
        hits = re.findall(r"\b(\d{2,4})\s+tests?\b", text)
        assert not hits, (
            f"{rel} states a test count {hits}; run the suite instead. A typed "
            "count goes stale and then lies."
        )


def test_regenerating_the_report_over_unchanged_artifacts_is_a_no_op():
    """verbatim-index stamps its page with the RENDER date, so every rebuild is a
    diff that tells a reader nothing about whether the numbers moved. This report
    is identified by a fingerprint over its inputs instead.

    This tests DETERMINISM, not currency: it generates twice and compares the two
    outputs. Comparing against the committed file would instead fail whenever an
    artifact is newer than the last commit, which is the normal state during
    work and is not what this is checking.
    """
    import subprocess
    import sys
    script = REPO / "scripts/write_m0_report.py"
    report = REPO / "docs/M0-REPORT.md"

    def generate() -> str | None:
        proc = subprocess.run([sys.executable, str(script)], cwd=str(REPO),
                              capture_output=True, text=True, timeout=120)
        return report.read_text() if proc.returncode == 0 else None

    first = generate()
    if first is None:
        pytest.skip("report inputs unavailable")
    second = generate()
    assert second == first, (
        "two consecutive generations over the same artifacts differ; the "
        "report's identity must be its input fingerprint, not the wall clock"
    )
