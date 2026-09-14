"""Does the cited evidence actually support what the rationale claims?

A contract hash says which bytes the model was shown. Citation ids say which
observations it named. Neither says the rationale is a fair reading of them, and
that gap is where a plausible, well-formatted, wrong score lives.

This module does the machine-checkable half and then hands a human the rest.
Nothing here decides that a rationale is CORRECT -- only a person reading the
evidence beside the claim can say that, and the report is built for exactly
that reading.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["GroundingCheck", "check_rationale", "AUTOMATED_CHECKS"]

#: Claims a rationale can make that the observation set must be able to support.
_MULTI_SOURCE = re.compile(
    r"\b(multiple|several|two|three|both) (independent )?(publications?|sources?|"
    r"publishers?|magazines?)\b", re.I)
#: Only UNAMBIGUOUSLY temporal claims fail. "consistently" and "sustained" are
#: the rubric's OWN band vocabulary ("the judgments consistently present the
#: person as notably attractive"), and a judge quoting the band it chose is not
#: claiming multi-year recognition. Measured 2026-09-14: the looser pattern
#: failed a correct single-period rationale for exactly that reason, and a check
#: that fires on correct work is a check that gets ignored.
_REPEATED = re.compile(
    r"\b(year after year|across (several|multiple|many) years|"
    r"in (several|multiple) (different )?years|"
    r"repeatedly (named|recognised|recognized|listed|placed)|"
    r"on (several|multiple) occasions|more than once)\b", re.I)
#: Softer vocabulary that MIGHT imply repetition. Warns, never fails.
_REPEATED_SOFT = re.compile(r"\b(repeated(ly)?|consistent(ly)?|sustained)\b", re.I)
_TOP_CLAIM = re.compile(r"\b(top[- ](of[- ]the[- ]list|placement|ten|decile)|"
                        r"number one|first place|winner|headline)\b", re.I)
_SUPERLATIVE = re.compile(r"\b(most|greatest|unmatched|without equal|the single)\b", re.I)

AUTOMATED_CHECKS = (
    "cites_at_least_one_observation",
    "every_cited_id_exists_in_the_dossier",
    "rationale_names_the_ids_it_cites",
    "multi_source_claim_matches_source_count",
    "repetition_claim_matches_period_count",
    "top_placement_claim_matches_a_rank_or_award",
)


@dataclass(frozen=True)
class GroundingCheck:
    estimate_id: str
    person: str
    period: str
    estimate: float | None
    failures: tuple[str, ...]
    warnings: tuple[str, ...]
    needs_human_read: bool
    rationale: str
    evidence_summary: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict:
        return {
            "estimate_id": self.estimate_id, "person": self.person,
            "period": self.period, "estimate": self.estimate,
            "failures": list(self.failures), "warnings": list(self.warnings),
            "passed_automated": self.passed,
            "needs_human_read": self.needs_human_read,
            "rationale": self.rationale,
            "evidence": list(self.evidence_summary),
        }


def check_rationale(
    *,
    estimate_id: str,
    person: str,
    period: str,
    estimate: float | None,
    rationale: str,
    cited_ids: list[str],
    dossier_ids: list[str],
    observations: list[dict],
) -> GroundingCheck:
    """Machine-checkable consistency between a rationale and its evidence.

    A FAILURE means the rationale asserts something the evidence cannot carry.
    A WARNING means it might, and a person should look.
    """
    failures: list[str] = []
    warnings: list[str] = []

    if not cited_ids:
        failures.append("cites_at_least_one_observation")
    unknown = [c for c in cited_ids if c not in dossier_ids]
    if unknown:
        failures.append(f"every_cited_id_exists_in_the_dossier: {unknown}")
    if cited_ids and not any(c in rationale for c in cited_ids):
        failures.append("rationale_names_the_ids_it_cites")

    sources = {o.get("original_source") or o.get("list_edition_id")
               for o in observations}
    publishers = {o.get("publisher") for o in observations if o.get("publisher")}
    periods = {o.get("concerns_period") for o in observations}

    if _MULTI_SOURCE.search(rationale) and len(sources) < 2:
        failures.append(
            f"multi_source_claim_matches_source_count: the rationale claims "
            f"several sources but the dossier has {len(sources)}"
        )
    if _REPEATED.search(rationale) and len(periods) < 2:
        failures.append(
            f"repetition_claim_matches_period_count: the rationale claims "
            f"recognition across years but the dossier covers {len(periods)} period(s)"
        )
    elif _REPEATED_SOFT.search(rationale) and len(periods) < 2:
        warnings.append(
            "repetition-flavoured wording on a single-period dossier; this is "
            "often the rubric's own band language rather than a claim about "
            "several years, so a person should judge which it is"
        )
    if _TOP_CLAIM.search(rationale):
        supports_top = any(
            o.get("evidence_type") == "editorial_award"
            or (o.get("evidence_type") == "ordered_rank"
                and (o.get("rank") or 999) <= max(1, (o.get("list_length") or 100) // 10))
            for o in observations
        )
        if not supports_top:
            failures.append(
                "top_placement_claim_matches_a_rank_or_award: the rationale "
                "claims a headline or top placement that no observation carries"
            )
    if _SUPERLATIVE.search(rationale) and len(publishers) < 2:
        warnings.append(
            "superlative language resting on a single publisher; a person should "
            "check the claim is about the judgment and not about the project"
        )
    if estimate is not None and estimate >= 90 and len(sources) < 2:
        warnings.append(
            "top-band estimate from one source; legitimate under the rubric, but "
            "worth a human read"
        )

    summary = tuple(
        f"[{o.get('observation_id')}] {o.get('evidence_type')} "
        f"{'rank ' + str(o.get('rank')) + ' of ' + str(o.get('list_length')) if o.get('rank') else ''}"
        f" | {o.get('publisher')} | concerns {o.get('concerns_period')} "
        f"| {o.get('excerpt', '')[:90]}"
        for o in observations
    )
    return GroundingCheck(
        estimate_id=estimate_id, person=person, period=period, estimate=estimate,
        failures=tuple(failures), warnings=tuple(warnings),
        needs_human_read=bool(failures or warnings),
        rationale=rationale, evidence_summary=summary,
    )
