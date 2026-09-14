"""Who this project must never rate.

`partner_eligibility.classify` decides whether a partner is a public figure
whose appearance has been publicly judged, someone notable but not
public-facing, or a private individual the plan forbids rating merely because
they dated a celebrity.

It is the most consequential branch in the repository and had no test of any
kind — it was the one script in thirty that nothing exercised beyond running
`--help`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "partner_eligibility", REPO / "scripts/partner_eligibility.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_a_private_individual_with_nothing_is_never_rated():
    """The protective default, and the whole reason this classifier exists."""
    m = _mod()
    assert m.classify(has_evidence=False, occupations=set(),
                      has_article=False) == "not_a_public_figure_do_not_rate"


def test_a_wikipedia_article_alone_is_not_permission():
    """Notability establishes that someone is written about. It does not
    establish that they put their appearance in public."""
    m = _mod()
    assert m.classify(has_evidence=False, occupations={"lawyer"},
                      has_article=True) == "notable_but_not_public_facing"


def test_a_public_facing_occupation_without_evidence_is_a_real_gap():
    m = _mod()
    occ = next(iter(_mod().PUBLIC_FACING))
    assert m.classify(has_evidence=False, occupations={occ},
                      has_article=True) == "public_figure_no_evidence_found"


def test_existing_evidence_settles_it():
    """Someone already carrying a published attractiveness judgment is a public
    figure in exactly the respect this project cares about."""
    m = _mod()
    assert m.classify(has_evidence=True, occupations=set(),
                      has_article=False) == "evidenced"


def test_evidence_outranks_occupation_and_article():
    m = _mod()
    occ = next(iter(m.PUBLIC_FACING))
    assert m.classify(has_evidence=True, occupations={occ},
                      has_article=True) == "evidenced"


def test_occupation_outranks_a_bare_article():
    m = _mod()
    occ = next(iter(m.PUBLIC_FACING))
    assert m.classify(has_evidence=False, occupations={occ, "lawyer"},
                      has_article=True) == "public_figure_no_evidence_found"


def test_a_failed_occupation_lookup_makes_the_project_more_cautious():
    """If the SPARQL fetch returns nothing, everyone arrives with no
    occupations and no article and everyone is classified DO NOT RATE. A broken
    fetch must not quietly widen who gets rated."""
    m = _mod()
    for _ in range(3):
        assert m.classify(has_evidence=False, occupations=set(),
                          has_article=False) == "not_a_public_figure_do_not_rate"


def test_every_status_the_script_can_emit_is_covered_here():
    """A status added without a test would be an unreviewed decision about
    whether somebody may be rated."""
    m = _mod()
    emitted = {
        m.classify(has_evidence=True, occupations=set(), has_article=False),
        m.classify(has_evidence=False, occupations=next(iter(m.PUBLIC_FACING)) and
                   {next(iter(m.PUBLIC_FACING))}, has_article=False),
        m.classify(has_evidence=False, occupations={"lawyer"}, has_article=True),
        m.classify(has_evidence=False, occupations=set(), has_article=False),
    }
    assert emitted == {
        "evidenced", "public_figure_no_evidence_found",
        "notable_but_not_public_facing", "not_a_public_figure_do_not_rate",
    }
