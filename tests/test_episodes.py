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


# -- why the merged episode takes the LAST stage's end -----------------------

def test_an_ongoing_stage_can_never_be_joined_from():
    """`merge_progressions` sets the merged end to `last.end`, where `last` is
    the final stage BY START DATE. That is only right if ends are
    non-decreasing along a run.

    They are, for two reasons worth writing down so nobody 'fixes' this into
    max() and changes the ids:

      - The join requires `prev.end is not None`, so a stage with no end is
        always last in its run. An ongoing episode therefore takes the ongoing
        stage's open end, never an earlier closed one.
      - The join window is JOIN_SLACK_DAYS = 1, so a later stage can begin at
        most one day before the previous ended. For its end to precede the
        previous end it would have to span less than a day.
    """
    from modules.records.episodes import JOIN_SLACK_DAYS
    assert JOIN_SLACK_DAYS == 1, (
        "widening this makes `last.end` unsafe: a stage could then start well "
        "before the previous ended and finish earlier, and the merged episode "
        "would end before one of its own stages. Use max() if you widen it."
    )


# ---------------------------------------------------------------------------
# Mirrored candidates: one Wikidata statement read off BOTH people's items.
#
# Found 2026-09-14. When both halves of a couple are in the cohort the fetcher
# reads the same statement twice. Those two candidates became two episodes, and
# for Ben Affleck + Ana de Armas the dates were identical, so the two episodes
# got the SAME stable_id -- anything keyed by episode_id then dropped one
# silently. The episode count read 31 for 29 distinct relationships.
# ---------------------------------------------------------------------------

def _mirror(c, subject="Q2", partner="Q1"):
    """The same statement as it arrives from the other person's item."""
    from dataclasses import replace
    return replace(c, episode_id=c.episode_id + "_mirror",
                   subject_qid=subject, partner_qid=partner)


def test_the_same_statement_from_both_items_is_one_episode():
    a = _c("unmarried_partner", "2020-03-01", "2021-01-31")
    eps = merge_progressions([a, _mirror(a)])
    assert len(eps) == 1, "one statement read twice is one relationship"
    assert eps[0].stages == ["unmarried_partner"]


def test_the_collapse_is_counted_not_swallowed():
    from modules.records.episodes import merge_progressions_with_stats
    a = _c("spouse", "2005-06-29", "2018-10-31")
    eps, collapsed = merge_progressions_with_stats([a, _mirror(a)])
    assert (len(eps), collapsed) == (1, 1)


def test_a_mirrored_duplicate_no_longer_collides_on_id():
    """Two episodes sharing an id is the bug that made this findable."""
    a = _c("unmarried_partner", "2020-03-01", "2021-01-31")
    eps = merge_progressions([a, _mirror(a)])
    assert len({e.episode_id for e in eps}) == len(eps)


def test_a_duplicate_does_not_block_a_real_progression():
    """The real Affleck/Garner shape: a duplicated spouse span plus a dating
    span that only one item carries. The progression must still merge."""
    dating = _c("unmarried_partner", "2004-10-01", "2005-06-29")
    spouse = _c("spouse", "2005-06-29", "2018-10-31")
    eps = merge_progressions([spouse, _mirror(spouse), dating])
    assert len(eps) == 1
    assert eps[0].stages == ["unmarried_partner", "spouse"]
    assert eps[0].start.value == "2004-10-01" and eps[0].end.value == "2018-10-31"


def test_statements_that_differ_are_kept_apart():
    """Only an EXACT match collapses.

    Two statements disagreeing on a date are two candidates, and the defect
    detector decides what that means. Collapsing them would pick a winner
    between two sources, which is not this function's call.
    """
    a = _c("spouse", "2005-06-29", "2018-10-31")
    b = _c("spouse", "2006-06-29", "2018-10-31", eid="c_other")
    eps = merge_progressions([a, b])
    assert len(eps) == 2


def test_differing_precision_is_not_an_exact_match():
    """2005 and 2005-06-29 are different claims, and the project stores
    precision precisely so they cannot be conflated."""
    from dataclasses import replace
    a = _c("spouse", "2005-06-29", "2018-10-31")
    b = replace(a, episode_id="c_year", start=_pd("2005", Precision.YEAR))
    eps = merge_progressions([a, b])
    assert len(eps) == 2


def test_a_reference_on_either_copy_survives():
    """Whether Wikidata cites a source is a property of the statement, not of
    which item it happened to be read from."""
    from dataclasses import replace
    a = replace(_c("spouse", "2005-06-29", "2018-10-31"), has_reference=False)
    eps = merge_progressions([a, replace(_mirror(a), has_reference=True)])
    assert len(eps) == 1 and eps[0].has_reference is True


def test_the_surviving_copy_does_not_depend_on_input_order():
    a = _c("spouse", "2005-06-29", "2018-10-31")
    m = _mirror(a)
    forward = merge_progressions([a, m])
    backward = merge_progressions([m, a])
    assert [e.episode_id for e in forward] == [e.episode_id for e in backward]
    assert forward[0].subject_qid == backward[0].subject_qid
