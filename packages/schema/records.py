"""Record types for the pairing-WAR pilot.

THE ONE RULE THIS FILE ENFORCES
-------------------------------
What a publication *said* and what this project *inferred* are different
records with different types.  An ``Observation`` holds only source-local
facts.  A ``StandingEstimate`` is always this project's inference -- it has no
``status`` field at all, because a field that can say "observed" is a field
through which a publication's own rating can leak back out and be read as a
measurement.

Non-appearance is not a record.  There is no evidence type for "was not on the
list", so an omission cannot be written down, which is how "omission does not
change a score" becomes structural rather than a promise.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from packages.temporal.dates import PreciseDate

__all__ = [
    "EvidenceType",
    "Lineage",
    "Observation",
    "Support",
    "StandingEstimate",
    "ListEdition",
    "MissingnessReason",
    "SchemaError",
    "ADJUDICATION_GAP",
    "reduce_judges",
]


class SchemaError(ValueError):
    """Raised instead of accepting a record that cannot be interpreted."""


class EvidenceType(str, Enum):
    ORDERED_RANK = "ordered_rank"
    UNORDERED_INCLUSION = "unordered_inclusion"
    EDITORIAL_AWARD = "editorial_award"
    PUBLICATION_RATING = "publication_rating"
    BALLOT_PREFERENCE = "ballot_preference"
    QUALITATIVE_COMMENTARY = "qualitative_commentary"


class MissingnessReason(str, Enum):
    NO_OBSERVATIONS = "no_observations"
    ALL_REJECTED_IN_REVIEW = "all_rejected_in_review"
    OUTSIDE_ADULT_WINDOW = "outside_adult_window"
    BEYOND_NEARBY_PERIOD_BOUND = "beyond_nearby_period_bound"
    SOURCE_ROUTE_RESTRICTED = "source_route_restricted"


@dataclass(frozen=True)
class Lineage:
    """Which edition a claim originally came from.

    Five sites reprinting one magazine's list are five copies of ONE
    observation.  Collapsing on ``original_source`` before a dossier is built
    is what stops copy volume acting as corroboration.
    """

    original_source: str
    is_syndicated_copy: bool = False


@dataclass(frozen=True)
class ListEdition:
    """One dated publication of one list, award or poll."""

    list_edition_id: str
    publisher: str
    title: str
    source_url: str
    published_at: PreciseDate
    concerns_period: PreciseDate
    access_route: str            # e.g. "wikipedia-api", "publisher-direct"
    retrieved_at_utc: str
    content_sha256: str
    candidate_set_described: str
    list_length: int | None = None
    licence: str | None = None
    attribution: str | None = None

    def __post_init__(self) -> None:
        if not self.candidate_set_described:
            raise SchemaError(
                f"{self.list_edition_id}: candidate_set_described is required. "
                "A list drawn from a different pool is weaker evidence about "
                "this pool, and the rubric cannot know that unless it is recorded."
            )
        if not self.access_route:
            raise SchemaError(f"{self.list_edition_id}: access_route is required")


@dataclass(frozen=True)
class Observation:
    """A source-local fact.  No inference of any kind lives here."""

    observation_id: str
    person_id: str
    list_edition_id: str
    evidence_type: EvidenceType
    observed: dict[str, Any]
    concerns_period: PreciseDate
    published_at: PreciseDate
    lineage: Lineage
    excerpt: str
    excerpt_locator: str
    retrospective: bool = False
    review_status: str = "pending"

    def __post_init__(self) -> None:
        checker = _OBSERVED_CHECKS[self.evidence_type]
        checker(self)
        if not self.excerpt_locator:
            raise SchemaError(
                f"{self.observation_id}: excerpt_locator is required so a human "
                "can find the claim on the page again"
            )


def _check_ordered_rank(o: Observation) -> None:
    obs = o.observed
    if not obs.get("order_is_ranking", False):
        raise SchemaError(
            f"{o.observation_id}: an ordered_rank observation needs "
            "order_is_ranking=True. Gallery order is not ranking order until "
            "the page says it is; record it as unordered_inclusion instead."
        )
    if not obs.get("order_basis"):
        raise SchemaError(
            f"{o.observation_id}: order_basis must quote the page text that "
            "establishes the order as a ranking"
        )
    rank, length = obs.get("rank"), obs.get("list_length")
    if not isinstance(rank, int) or rank < 1:
        raise SchemaError(f"{o.observation_id}: rank must be a positive integer")
    if not isinstance(length, int) or length < rank:
        raise SchemaError(
            f"{o.observation_id}: list_length must be an integer >= rank"
        )


def _check_unordered_inclusion(o: Observation) -> None:
    if "rank" in o.observed:
        raise SchemaError(
            f"{o.observation_id}: an unordered_inclusion observation may not "
            "carry a rank. Do not invent an order the source did not state."
        )
    if "list_length" not in o.observed:
        raise SchemaError(
            f"{o.observation_id}: list_length is required; use None when the "
            "source does not state a size"
        )
    length = o.observed["list_length"]
    if length is None:
        return                      # "size not stated" is a legitimate value
    if not isinstance(length, int) or length < 1:
        raise SchemaError(
            f"{o.observation_id}: list_length {length!r} is not a real size. A "
            "list of zero people is not a thing, and rendering it told the judge "
            "'a set of 0 names'. Use None for an unstated size."
        )


def _check_editorial_award(o: Observation) -> None:
    if not o.observed.get("award_name"):
        raise SchemaError(f"{o.observation_id}: award_name is required")
    if "rank" in o.observed:
        raise SchemaError(
            f"{o.observation_id}: an award is not a rank over a population"
        )


def _check_publication_rating(o: Observation) -> None:
    obs = o.observed
    if "rating_value" not in obs or not obs.get("rating_scale"):
        raise SchemaError(
            f"{o.observation_id}: rating_value and rating_scale are both required. "
            "This is the PUBLICATION's number on the PUBLICATION's scale."
        )


def _check_ballot_preference(o: Observation) -> None:
    obs = o.observed
    share = obs.get("vote_share")
    if not isinstance(share, (int, float)) or not 0 <= share <= 1:
        raise SchemaError(f"{o.observation_id}: vote_share must be in [0, 1]")
    if not obs.get("ballot_description"):
        raise SchemaError(
            f"{o.observation_id}: ballot_description is required. A share means "
            "nothing without knowing what was on the ballot."
        )
    if obs.get("placement") is None and obs.get("outcome_published") is not True:
        # A 30% share among 20 options is NOT established as a plurality.
        if "is_plurality" in obs:
            raise SchemaError(
                f"{o.observation_id}: is_plurality may not be asserted without "
                "the published outcome. A 30% share can still place second."
            )


def _check_qualitative(o: Observation) -> None:
    if not o.excerpt.strip():
        raise SchemaError(
            f"{o.observation_id}: qualitative commentary needs the excerpt itself"
        )
    for numeric in ("rank", "rating_value", "vote_share"):
        if numeric in o.observed:
            raise SchemaError(
                f"{o.observation_id}: qualitative commentary carries no {numeric}"
            )


_OBSERVED_CHECKS = {
    EvidenceType.ORDERED_RANK: _check_ordered_rank,
    EvidenceType.UNORDERED_INCLUSION: _check_unordered_inclusion,
    EvidenceType.EDITORIAL_AWARD: _check_editorial_award,
    EvidenceType.PUBLICATION_RATING: _check_publication_rating,
    EvidenceType.BALLOT_PREFERENCE: _check_ballot_preference,
    EvidenceType.QUALITATIVE_COMMENTARY: _check_qualitative,
}


@dataclass(frozen=True)
class Support:
    """Everything about the EVIDENCE.  Never adds or subtracts estimate points."""

    distinct_original_sources: int
    distinct_publishers: int
    reliability: str
    specificity: str
    contemporaneity: str
    across_judges_gap: float | None = None
    source_disagreement: str | None = None
    periods_with_evidence: int = 0
    periods_needed: int = 0

    @property
    def level(self) -> str:
        if self.distinct_original_sources <= 1:
            return "single_source"
        return "multi_publisher" if self.distinct_publishers > 1 else "single_publisher"


#: Two judges detect a disagreement but cannot resolve it, so a wide gap is
#: escalated to human adjudication rather than silently averaged.
ADJUDICATION_GAP = 10.0


def reduce_judges(scores: dict[str, float]) -> tuple[float | None, bool]:
    """Combine judge estimates.  Returns (reduced, needs_adjudication).

    With J = 2 the reducer is the arithmetic MEAN, and it is called a mean
    because a median of two *is* a mean; naming it a median would misdescribe
    what the number is.
    """
    if not scores:
        return None, False
    values = list(scores.values())
    gap = max(values) - min(values)
    return sum(values) / len(values), gap > ADJUDICATION_GAP


@dataclass(frozen=True)
class StandingEstimate:
    """This project's inferred score.  ALWAYS inferred -- there is no status field.

    ``periods`` is a list so that one estimate reused across adjacent periods
    keeps ONE identity.  The sensitivity simulation draws it once and applies
    that single draw to every period key, which is what keeps mirrored gaps
    exact negatives.  Three period keys must not become three draws.
    """

    estimate_id: str
    person_id: str
    periods: tuple[str, ...]
    estimate: float | None
    rubric_version: str
    contract_id: str
    judges: dict[str, float]
    reducer: str
    evidence_ids: tuple[str, ...]
    support: Support | None
    rationale: str
    needs_adjudication: bool = False
    method: str = "RES"
    scale: str = "pairing-war-standing-v2 (0-100)"
    missingness_reason: MissingnessReason | None = None
    period_support: str = "contemporaneous"

    def __post_init__(self) -> None:
        if self.estimate is None:
            if self.missingness_reason is None:
                raise SchemaError(
                    f"{self.estimate_id}: an unscored estimate must say why. "
                    "Missing is missing; it is not zero and not a low score."
                )
            if self.evidence_ids:
                raise SchemaError(
                    f"{self.estimate_id}: unscored but cites evidence"
                )
        else:
            if not 0 <= self.estimate <= 100:
                raise SchemaError(f"{self.estimate_id}: estimate out of range")
            if not self.evidence_ids:
                raise SchemaError(
                    f"{self.estimate_id}: a score with no cited observation is a "
                    "model-memory guess, which the rubric forbids"
                )
            if self.missingness_reason is not None:
                raise SchemaError(f"{self.estimate_id}: scored but flagged missing")
            if not self.rationale.strip():
                raise SchemaError(f"{self.estimate_id}: a score needs its rationale")
        if not self.periods:
            raise SchemaError(f"{self.estimate_id}: periods must not be empty")
        if len(set(self.periods)) != len(self.periods):
            raise SchemaError(f"{self.estimate_id}: duplicate period keys")
