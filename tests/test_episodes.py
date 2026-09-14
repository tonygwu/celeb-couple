"""Episode merging, defect flagging, and the adult window."""

from __future__ import annotations

from dataclasses import dataclass

from packages.temporal.dates import Interval, Precision, PreciseDate
from modules.records.episodes import Defect, adult_window, merge_progressions


def _pd(v, p=Precision.YEAR):
    return PreciseDate(v, p, "c_1")


@dataclass(frozen=True)
class Cand:
    episode_id: str
    pair_key: str
    subject_qid: str
    partner_qid: str
    partner_label: str
    relation: str
    start: PreciseDate | None
    end: PreciseDate | None
    has_reference: bool = True


def _c(rel, start, end, label="Partner", eid=None, sp=Precision.DAY, ep=Precision.DAY):
    return Cand(
        episode_id=eid or f"c_{rel}_{start}", pair_key="Q1|Q2",
        subject_qid="Q1", partner_qid="Q2", partner_label=label, relation=rel,
        start=None if start is None else _pd(start, sp),
        end=None if end is None else _pd(end, ep),
    )


def test_dating_then_marriage_merges_into_one_episode():
    """Observed in the pilot: Wikidata stores the progression as two statements."""
    eps = merge_progressions([
        _c("unmarried_partner", "1998-01-01", "2000-07-29"),
        _c("spouse", "2000-07-29", "2005-10-02"),
    ])
    assert len(eps) == 1, "a progression is one episode, not two scoring chances"
    ep = eps[0]
    assert ep.stages == ["unmarried_partner", "spouse"]
    assert ep.start.value == "1998-01-01" and ep.end.value == "2005-10-02"
    assert len(ep.merged_from) == 2


def test_a_documented_separate_reconciliation_stays_a_separate_episode():
    eps = merge_progressions([
        _c("unmarried_partner", "2002-01-01", "2004-01-01"),
        _c("spouse", "2022-07-16", "2024-01-01"),
    ])
    assert len(eps) == 2, "a twenty-year gap is not one continuous episode"


def test_an_end_before_its_start_is_flagged_not_silently_swapped():
    """Found live in the pilot cohort."""
    eps = merge_progressions([_c("unmarried_partner", "2021-01-01", "2020-01-01")])
    kinds = [d.kind for d in eps[0].defects]
    assert "end_before_start" in kinds
    assert eps[0].scorable is False
    assert eps[0].start.value == "2021-01-01", "the dates are left exactly as sourced"


def test_a_candidate_with_no_start_date_is_flagged():
    eps = merge_progressions([_c("spouse", None, None)])
    assert "no_start_date" in [d.kind for d in eps[0].defects]
    assert eps[0].scorable is False


def test_an_unresolved_partner_label_is_flagged():
    """Found live: the label service returned a bare Q-id for two partners."""
    eps = merge_progressions([_c("spouse", "2014-08-23", "2019-04-12", label="Q13909")])
    assert "partner_label_unresolved" in [d.kind for d in eps[0].defects]


def test_a_clean_episode_carries_no_defects_and_is_scorable():
    eps = merge_progressions([_c("spouse", "2005-06-29", "2018-10-01")])
    assert eps[0].defects == [] and eps[0].scorable is True


# -- the adult window -------------------------------------------------------

def _span(a, b):
    return Interval(_pd(a, Precision.DAY), _pd(b, Precision.DAY))


def test_an_episode_is_clipped_to_where_both_people_were_eighteen():
    iv = Interval(_pd("2003-01-01", Precision.DAY), _pd("2007-12-31", Precision.DAY))
    clipped, reason = adult_window(
        iv, _pd("1980-01-01", Precision.DAY), _pd("1987-06-01", Precision.DAY)
    )
    assert reason is None
    assert clipped.first_day().isoformat() == "2005-06-01", "the later 18th birthday wins"
    assert clipped.last_day().isoformat() == "2007-12-31"


def test_an_unknown_birth_date_excludes_rather_than_assuming_adulthood():
    iv = Interval(_pd("2003-01-01", Precision.DAY), _pd("2007-12-31", Precision.DAY))
    clipped, reason = adult_window(iv, _pd("1980-01-01", Precision.DAY), None)
    assert clipped is None and reason == "both_parties_adult_window_unknown"


def test_a_wholly_underage_episode_is_excluded_with_its_reason():
    iv = Interval(_pd("2003-01-01", Precision.DAY), _pd("2004-12-31", Precision.DAY))
    clipped, reason = adult_window(
        iv, _pd("1990-01-01", Precision.DAY), _pd("1991-01-01", Precision.DAY)
    )
    assert clipped is None and reason == "outside_adult_window"


def test_a_year_precision_birth_date_uses_the_conservative_reading():
    """Born "1987" could be 31 December, so adulthood starts no earlier than 2005-12-31."""
    iv = Interval(_pd("2005-01-01", Precision.DAY), _pd("2007-12-31", Precision.DAY))
    clipped, _ = adult_window(
        iv, _pd("1970-01-01", Precision.DAY), _pd("1987", Precision.YEAR)
    )
    assert clipped.first_day().isoformat() == "2005-12-31"


def test_a_leap_day_birth_date_does_not_crash_the_eighteenth_birthday():
    iv = Interval(_pd("2010-01-01", Precision.DAY), _pd("2012-12-31", Precision.DAY))
    clipped, _ = adult_window(
        iv, _pd("1970-01-01", Precision.DAY), _pd("1992-02-29", Precision.DAY)
    )
    assert clipped.first_day().isoformat() == "2010-03-01"
