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
import sys

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
    assert len(blob["rows"]) >= 5, (
        "an empty rows list makes every comparison below vacuous")
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
    assert len(blob["ladder"]) >= 5, "an empty ladder checks nothing"
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
    assert len(blob["options"]) >= 3, "an empty options list checks nothing"
    for option in blob["options"]:
        line = next((l for l in md.splitlines()
                     if l.startswith("|") and option["name"] in l), None)
        assert line is not None, f"no row for {option['name']!r}"
        assert f"**{option['count']}** of {option['of']}" in line, (
            f"row for {option['name']!r} reads {line!r}, artifact says "
            f"{option['count']} of {option['of']}"
        )


def test_the_readme_headline_numbers_match_the_measurements():
    """The README must lead with the UNBIASED estimator.

    This test used to assert the README contained the ETA-squared percentage,
    which is the superseded, biased number. It passed only because the README
    mentions 39% in the sentence explaining that eta is biased upward. So the
    guard had it exactly backwards: tidying the historical note away would have
    failed it, and replacing the headline 31% with anything at all would not.
    A test pinned to the wrong statistic is worse than no test, because it
    reads as coverage.
    """
    density = _artifact("data/pilot/run/evidence_density.json")
    shape = _artifact("data/pilot/run/shape_confound.json")
    readme = _doc("README.md")
    omega = round((shape["omega_squared_shape_explains"] or 0) * 100)
    assert f"{omega}% of the estimate" in readme, (
        f"README should lead with omega-squared: shape explains {omega}% of "
        f"the estimate"
    )
    eta = round((shape["eta_squared_shape_explains"] or 0) * 100)
    if f"{eta}%" in readme:
        assert "eta-squared" in readme and "biased" in readme, (
            f"the README names {eta}%, the biased eta-squared value, without "
            "saying which estimator it is or that it is superseded"
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


# -- measurements do not belong in source docstrings -------------------------

#: Files whose docstrings NARRATE a superseded measurement to explain why it
#: was wrong. That is history, not a claim about the present, and removing it
#: would delete the reasoning. Everything else must point at the artifact.
_NARRATES_HISTORY = {
    "scripts/audit_doc_numbers.py",      # explains the 42% that went stale
    "scripts/measure_rater_noise.py",    # explains the pooled LSD of 1.2
}

_STANDING_MEASUREMENT = __import__("re").compile(
    r"explains \d+%|\d+% of the (?:estimate|variance)|LSD of \d",
    __import__("re").I)


def test_no_source_docstring_states_a_current_measurement():
    """`modules/analytics/comparability.py` opened with "evidence type alone
    explains 42% of the variance" for hours after the re-score made it 39%.
    `scripts/audit_doc_numbers.py` checks Markdown, and a docstring is read by
    the next person exactly as confidently as a document.

    Widening that audit to `*.py` was tried and reverted: most hits were test
    fixtures and deliberate historical references, and a guard that raises
    false alarms is one nobody believes. So the rule is simpler -- source says
    "a large share, see the artifact" and never a figure -- and this enforces
    it, with an explicit allowlist for the two files that narrate history.
    """
    import subprocess
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    tracked = subprocess.run(
        ["git", "ls-files", "modules/*.py", "packages/*.py", "scripts/*.py"],
        cwd=repo, capture_output=True, text=True, check=True).stdout.split()

    offenders = []
    for rel in tracked:
        if rel in _NARRATES_HISTORY:
            continue
        for i, line in enumerate((repo / rel).read_text().splitlines(), 1):
            if _STANDING_MEASUREMENT.search(line):
                offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, (
        "a measurement typed into source goes stale and then lies. Point at "
        "the artifact instead:\n  " + "\n  ".join(offenders))


def test_no_document_claims_cross_family_agreement_on_the_real_dossiers():
    """The claim appeared in three documents and was wrong in all of them:
    README.md said "Two model families agree closely on real dossiers",
    docs/THE-TRAP.md said "two model families agree closely", and the M0
    report's opening said "Two model families independently agreed".

    Only one family scored the real dossiers -- codex reached 0% of its quota
    window mid-run. Two families DID agree on the synthetic stress corpus, and
    the distinction is the whole point: agreement on constructed cases says the
    rubric is legible, agreement on real evidence would say the estimates are
    not one family's idiosyncrasy. Only the first was measured.

    This asserts the claim against the SCORES, so it relaxes on its own the
    moment a second family actually runs.
    """
    import json
    import re
    import subprocess
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    scores = repo / "data/pilot/run/evidenced_scores.json"
    if not scores.exists():
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")

    blob = json.loads(scores.read_text())
    families = {j for r in blob["person_periods"] for j in r["judges"]}
    if len(families) > 1:
        return          # a second family ran; the claim would be true

    tracked = subprocess.run(["git", "ls-files", "*.md"], cwd=repo,
                             capture_output=True, text=True, check=True).stdout.split()
    # Stop at a semicolon as well as a full stop. The first version matched
    # across one, and flagged the CORRECT sentence "Two model families agree
    # closely on the SYNTHETIC corpus; on the real dossiers only one family
    # ran" -- a false alarm from the guard written to catch the false claim,
    # which is the failure mode that teaches people to ignore guards.
    pattern = re.compile(
        r"families?\s+(?:agree|agreed)[^.;]{0,80}real dossiers", re.I)
    offenders = [p for p in tracked if pattern.search((repo / p).read_text())]
    assert not offenders, (
        f"only {sorted(families)} scored the real dossiers, but these claim "
        f"cross-family agreement on them: {offenders}"
    )


def test_the_cross_family_guard_catches_the_claim_it_was_written_for():
    """And does not fire on the corrected sentence. A guard tested only against
    a clean repository passes whether or not it works."""
    import re
    pattern = re.compile(
        r"families?\s+(?:agree|agreed)[^.;]{0,80}real dossiers", re.I)

    wrong = "Two model families agree closely on real dossiers."
    assert pattern.search(wrong), "the guard must catch the claim it exists for"

    right = ("Two model families agree closely on the SYNTHETIC corpus; on the "
             "real dossiers only one family ran.")
    assert not pattern.search(right), "and must not fire on the correction"


#: Documents a script owns end to end, and the script that owns each.
GENERATED_DOCS = {
    "docs/M0-REPORT.md": "scripts/write_m0_report.py",
    "docs/SCALING.md": "scripts/scaling_report.py",
    "docs/REACHABLE-PRODUCTS.md": "scripts/reachable_products.py",
    "docs/GROUNDING-AUDIT.md": "scripts/grounding_audit.py",
}


def test_every_generated_document_regenerates_identically():
    """A generated document with hand-appended sections is a trap.

    docs/SCALING.md had the whole source-requirement ladder written into it by
    hand, and `scaling_report.py` rewrites the file from scratch. Running the
    generator deleted the section, so nobody ran the generator, so the
    generated half sat stale: a pilot column describing a 35-observation corpus
    while the corpus held 41.

    Regenerating and finding the file unchanged proves both halves of what
    matters -- the document is current, and the generator owns all of it.

    The original bytes are RESTORED afterwards, because the generators write
    to the tracked path and this test used to leave the repaired file behind.
    That made the verdict self-healing: a drifted document failed once and
    passed on the next run with nothing fixed, which is indistinguishable from
    a flaky test and hides exactly what this is for. It also left a dirty tree
    for whoever ran the suite. Reporting drift is this test's job; repairing it
    is `bash scripts/run_chain.sh reports`.
    """
    import hashlib
    import subprocess
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent
    # sys.executable: CI has no .venv, and a skip keyed on one would make this
    # guard silently inert exactly where it matters most.
    py = Path(sys.executable)
    if not (repo / "data/pilot/run").exists():
        pytest.skip("data/ is gitignored; nothing to regenerate in a fresh clone")

    def _hash(p):
        return hashlib.sha256((repo / p).read_bytes()).hexdigest()

    drifted = []
    for doc, script in GENERATED_DOCS.items():
        if not (repo / doc).exists():
            continue
        original = (repo / doc).read_bytes()
        before = _hash(doc)
        try:
            r = subprocess.run([str(py), str(repo / script)],
                               capture_output=True, text=True, cwd=repo, timeout=180)
            if r.returncode != 0:
                continue      # a missing input is a different test's problem
            if _hash(doc) != before:
                drifted.append(f"{doc} (regenerated by {script})")
        finally:
            # Unconditional: a generator that half-wrote and then raised would
            # otherwise leave a truncated document in the tree.
            (repo / doc).write_bytes(original)

    assert not drifted, (
        "these documents are not what their generator produces — either they "
        "were hand-edited, or their inputs moved and nobody re-ran:\n  "
        + "\n  ".join(drifted))


def test_the_joint_coverage_denominators_reconcile():
    """`candidate_pairings` is the headline denominator — "4 of 51" — and some
    of those 51 can never contribute. A film with an unparseable release year
    and an episode with no adult year were both skipped silently, so the
    denominator could shrink with no record of it.

    Both are now counted, and the episode figure must agree with the episodes
    artifact's own count of what it excluded.
    """
    import json
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    j = repo / "data/pilot/run/joint_with_nearby.json"
    e = repo / "data/pilot/records/episodes.json"
    if not (j.exists() and e.exists()):
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")

    d = json.loads(j.read_text())["denominators"]
    eps = json.loads(e.read_text())["episodes"]

    assert (d["candidate_pairings"]
            == d["episodes_examined"] + d["films_examined"])

    no_year = sum(1 for ep in eps if not (ep.get("adult_years") or []))
    assert d["episodes_contributing_no_adult_year"] == no_year, (
        "the count of episodes that cannot contribute must match the artifact"
    )
    assert d["films_skipped_no_parseable_year"] == len(d["films_skipped_detail"])


def test_no_artifact_reading_states_a_stale_corpus_size():
    """`alignment_gap.json`'s reading said "growing the corpus from 13
    observations to 25 did not move joint coverage". The corpus is 41, and the
    M0 report renders the same sentence from the density artifact — so the
    report said 41 while this artifact said 25, for anyone reading the JSON.

    Every artifact that mentions the corpus size must take it from the corpus.
    """
    import json
    import re
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    obs = repo / "data/pilot/observations/observations.json"
    if not obs.exists():
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")

    n = len(json.loads(obs.read_text())["observations"])
    for rel in ("data/pilot/run/alignment_gap.json",
                "data/pilot/run/evidence_density.json"):
        f = repo / rel
        if not f.exists():
            continue
        reading = json.loads(f.read_text()).get("reading") or ""
        for stated in re.findall(r"(\d+) observations", reading):
            assert int(stated) == n, (
                f"{rel} says {stated} observations; the corpus holds {n}")


def test_claude_md_is_still_a_symlink_to_agents_md():
    """CLAUDE.md and AGENTS.md are one file, so an agent reading either gets
    the same rules. Some editors and tools replace a symlink with a copy, after
    which the two drift apart silently and half the fleet reads stale rules.

    Git records the mode, so this checks what is committed rather than what
    happens to be on disk.
    """
    import subprocess
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    out = subprocess.run(["git", "ls-files", "-s", "CLAUDE.md"], cwd=repo,
                         capture_output=True, text=True, check=True).stdout
    assert out.startswith("120000"), (
        f"CLAUDE.md is committed as mode {out.split()[0] if out else 'missing'}, "
        "not a symlink (120000). It and AGENTS.md must stay one file."
    )
    assert (repo / "CLAUDE.md").read_text() == (repo / "AGENTS.md").read_text()
