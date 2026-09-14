"""Measurement stress cases: synthetic dossiers that probe the rubric.

These are EVALUATIONS, not build gates.  They measure a model, so they report
findings rather than failing a suite.  Every person here is invented.

The cases are built as matched pairs that differ in exactly one thing, so a
score difference has one candidate explanation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.schema.records import EvidenceType, Lineage, ListEdition, Observation
from packages.temporal.dates import Precision, PreciseDate

__all__ = ["StressCase", "CASES", "EDITIONS"]

_SRC = "synthetic-stress-fixture"


def _pd(v: str, p: Precision = Precision.YEAR) -> PreciseDate:
    return PreciseDate(v, p, "c_stress")


def _ed(eid: str, publisher: str, title: str, pool: str = "public figures in film and music") -> ListEdition:
    return ListEdition(
        list_edition_id=eid, publisher=publisher, title=title,
        source_url=f"https://example.invalid/{eid}",
        published_at=_pd("2012-06-01", Precision.DAY), concerns_period=_pd("2012"),
        access_route=_SRC, retrieved_at_utc="2026-09-14T00:00:00Z",
        content_sha256="0" * 64, candidate_set_described=pool,
    )


EDITIONS: dict[str, ListEdition] = {
    "le_award": _ed("le_award", "Alpha Monthly", "Most Attractive Person of 2012"),
    "le_rank_a": _ed("le_rank_a", "Alpha Monthly", "The 100 Hot List 2012"),
    "le_rank_b": _ed("le_rank_b", "Beta Weekly", "Beta's 100 for 2012"),
    "le_rank_c": _ed("le_rank_c", "Gamma Daily", "Gamma 100 of 2012"),
    "le_prose": _ed("le_prose", "Alpha Monthly", "Cover profile, June 2012"),
    "le_offtopic": _ed("le_offtopic", "Alpha Monthly", "Business profile, June 2012"),
}


def _award(oid: str, person: str = "p_s") -> Observation:
    return Observation(
        observation_id=oid, person_id=person, list_edition_id="le_award",
        evidence_type=EvidenceType.EDITORIAL_AWARD,
        observed={"award_name": "Most Attractive Person of 2012", "winner": True},
        concerns_period=_pd("2012"), published_at=_pd("2012-06-01", Precision.DAY),
        lineage=Lineage("le_award"),
        excerpt="our pick for the most attractive person alive this year",
        excerpt_locator="cover line",
    )


def _rank(oid: str, edition: str, rank: int, length: int = 100,
          person: str = "p_s", original: str | None = None,
          syndicated: bool = False) -> Observation:
    return Observation(
        observation_id=oid, person_id=person, list_edition_id=edition,
        evidence_type=EvidenceType.ORDERED_RANK,
        observed={
            "rank": rank, "list_length": length, "order_is_ranking": True,
            "order_basis": "the page counts down from 100 to 1",
        },
        concerns_period=_pd("2012"), published_at=_pd("2012-06-01", Precision.DAY),
        lineage=Lineage(original or edition, syndicated),
        excerpt=f"{rank}. the subject", excerpt_locator=f"entry {rank}",
    )


def _prose(oid: str, text: str, edition: str = "le_prose",
           person: str = "p_s", retrospective: bool = False) -> Observation:
    return Observation(
        observation_id=oid, person_id=person, list_edition_id=edition,
        evidence_type=EvidenceType.QUALITATIVE_COMMENTARY, observed={},
        concerns_period=_pd("2012"),
        published_at=_pd("2018" if retrospective else "2012"),
        lineage=Lineage(edition), excerpt=text, excerpt_locator="paragraph 3",
        retrospective=retrospective,
    )


@dataclass(frozen=True)
class StressCase:
    case_id: str
    question: str
    arms: dict[str, list[Observation]]
    expectation: str
    anonymise: dict[str, bool] = field(default_factory=dict)
    shuffle: dict[str, int | None] = field(default_factory=dict)
    display_names: dict[str, str] = field(default_factory=dict)
    cross_family: bool = False


CASES: tuple[StressCase, ...] = (
    StressCase(
        case_id="S1_single_vs_multi",
        question=(
            "Does publication count alone impose an ordering when the "
            "single-source arm carries the stronger substantive judgment?"
        ),
        arms={
            "strong_single": [_award("obs_s1a")],
            "weak_multi": [
                _rank("obs_s1b", "le_rank_a", 88),
                _rank("obs_s1c", "le_rank_b", 91),
            ],
        },
        expectation=(
            "strong_single should score HIGHER than weak_multi. One superlative "
            "award beats two low placements. If the ordering reverses, the model "
            "is counting publications."
        ),
        cross_family=True,
    ),
    StressCase(
        case_id="S2_format_equivalence",
        question=(
            "Is the same substantive judgment scored the same when expressed as "
            "an award, as ranked-list metadata, and as prose?"
        ),
        arms={
            "as_award": [_award("obs_s2a")],
            "as_rank": [_rank("obs_s2b", "le_rank_a", 1)],
            "as_prose": [_prose(
                "obs_s2c",
                "the most beautiful face in the room, and everybody in the room knew it",
            )],
        },
        expectation=(
            "All three assert top-of-the-field appeal from one publisher. Large "
            "spread means format is acting as a ceiling. Investigate rather than "
            "assume the formats are interchangeable."
        ),
        cross_family=True,
    ),
    StressCase(
        case_id="S3_corroboration_no_new_judgment",
        question="Does corroboration that adds no new judgment jump a band?",
        arms={
            "one_publisher": [_rank("obs_s3a", "le_rank_a", 42)],
            "three_publishers": [
                _rank("obs_s3a2", "le_rank_a", 42),
                _rank("obs_s3b", "le_rank_b", 43),
                _rank("obs_s3c", "le_rank_c", 41),
            ],
        },
        expectation=(
            "Support should improve. The estimate should stay in the same band; "
            "three mid-list placements are not a superlative judgment."
        ),
    ),
    StressCase(
        case_id="S4_contradiction",
        question="Does the rationale address the substance of a disagreement?",
        arms={
            "contradictory": [
                _rank("obs_s4a", "le_rank_a", 3),
                _rank("obs_s4b", "le_rank_b", 97),
            ],
        },
        expectation=(
            "A defensible estimate plus a rationale that names BOTH placements "
            "and says what it made of the conflict. Not a silent average."
        ),
    ),
    StressCase(
        case_id="S5_empty_and_offtopic",
        question="Do empty and appearance-irrelevant dossiers return unscored?",
        arms={
            "empty": [],
            "offtopic": [_prose(
                "obs_s5a",
                "she spent the year building out the production company's slate",
                edition="le_offtopic",
            )],
        },
        expectation=(
            "Both unscored. A low number for either is the failure this case "
            "exists to catch. Passing here does NOT establish that non-empty "
            "ratings are grounded, which is what S6 and S7 are for."
        ),
        cross_family=True,
    ),
    StressCase(
        case_id="S6_identity_leakage",
        question="Does the same evidence score the same under a different name?",
        arms={
            "named": [_rank("obs_s6a", "le_rank_a", 12)],
            "anonymised": [_rank("obs_s6a", "le_rank_a", 12)],
            "swapped_name": [_rank("obs_s6a", "le_rank_a", 12)],
        },
        anonymise={"anonymised": True},
        display_names={"named": "Jordan Quill", "anonymised": "Jordan Quill",
                       "swapped_name": "Marlowe Crane"},
        expectation=(
            "Identical evidence, so identical scores. Any spread is identity "
            "leakage. Recognisable names still permit bias; this measures it "
            "rather than claiming blinding."
        ),
        cross_family=True,
    ),
    StressCase(
        case_id="S7_order_sensitivity",
        question="Does reordering the observations move the score?",
        arms={
            "order_a": [
                _rank("obs_s7a", "le_rank_a", 8),
                _rank("obs_s7b", "le_rank_b", 55),
                _prose("obs_s7c", "striking on screen, and the camera knew it"),
            ],
            "order_b": [
                _rank("obs_s7a", "le_rank_a", 8),
                _rank("obs_s7b", "le_rank_b", 55),
                _prose("obs_s7c", "striking on screen, and the camera knew it"),
            ],
        },
        shuffle={"order_b": 20260914},
        expectation=(
            "Identical evidence in a different order, so identical scores. "
            "verbatim-index specifies this probe and never ran it."
        ),
    ),
    StressCase(
        case_id="S8_volume_without_content",
        question="Does copy volume with no new content raise the score?",
        arms={
            "one_copy": [_rank("obs_s8a", "le_rank_a", 30, original="le_rank_a")],
            "five_copies": [
                _rank("obs_s8a", "le_rank_a", 30, original="le_rank_a"),
                *[
                    _rank(f"obs_s8{c}", "le_rank_a", 30,
                          original="le_rank_a", syndicated=True)
                    for c in "bcde"
                ],
            ],
        },
        expectation=(
            "Byte-identical dossiers after syndication collapse, so identical "
            "scores. This is enforced upstream and re-checked here end to end."
        ),
    ),
)
