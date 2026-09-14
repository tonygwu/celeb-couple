"""Score one dossier with J judges and reduce to one StandingEstimate.

Order of operations is load-bearing:
  1. spend the budget slot (so a cap halts BEFORE a call, not after)
  2. call the judge
  3. write the raw text to disk, BEFORE parsing
  4. parse, validate, and only then build a record

A judge that cites no observation from the dossier is rejected as a
model-memory guess, which is the failure the rubric's rule 10 exists to catch.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from packages.ids.keys import stable_id
from packages.llmkit.budget import Budget, BudgetExhausted
from packages.llmkit.contract import GradingContract
from packages.llmkit.judges import Judge, JudgeError
from packages.llmkit.taxonomy import (
    E_CITES_NOTHING,
    E_JSON_PARSE,
    E_NO_JSON,
    E_SCHEMA,
)
from packages.schema.records import (
    MissingnessReason,
    StandingEstimate,
    Support,
    reduce_judges,
)
from modules.consensus.dossier import Dossier

__all__ = ["score_dossier", "JudgeVerdict", "parse_verdict", "build_prompt"]


@dataclass(frozen=True)
class JudgeVerdict:
    judge: str
    scored: bool
    estimate: float | None
    band: str | None
    rationale: str
    evidence_ids: tuple[str, ...]
    support: dict
    missingness_reason: str | None
    telemetry: dict
    raw_path: str


_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def build_prompt(dossier: Dossier, rubric_text: str, schema_text: str) -> str:
    return (
        f"{rubric_text}\n\n"
        "---\n\n"
        "Your output must validate against this JSON schema:\n\n"
        f"{schema_text}\n\n"
        "---\n\n"
        f"DOSSIER (dossier_id: {dossier.dossier_id})\n\n"
        f"{dossier.text}\n"
        "---\n\n"
        "Return the JSON object and nothing else."
    )


def parse_verdict(text: str, dossier: Dossier, judge: str, telemetry: dict,
                  raw_path: str) -> JudgeVerdict:
    match = _JSON_BLOCK.search(text or "")
    if not match:
        raise JudgeError(E_NO_JSON, f"{judge} returned no JSON object")
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise JudgeError(E_JSON_PARSE, f"{judge}: {exc}") from exc

    if obj.get("schema_version") != "standing-estimate-2.0":
        raise JudgeError(E_SCHEMA, f"{judge}: wrong schema_version {obj.get('schema_version')!r}")

    scored = obj.get("scored")
    if not isinstance(scored, bool):
        raise JudgeError(E_SCHEMA, f"{judge}: scored must be a boolean")

    est = obj.get("estimate")
    cited = tuple(obj.get("evidence_ids") or ())
    rationale = (obj.get("rationale") or "").strip()

    if scored:
        # `isinstance(True, int)` is True in Python and `0 <= True <= 100` is
        # too, so a bare `"estimate": true` passed this check and became the
        # value 1 downstream: a score of 1 out of 100, indistinguishable in the
        # artifact from a judge that meant it. `scored` is checked with an
        # explicit isinstance(bool) a few lines up, so the distinction was
        # known here; this one inherited Python's default.
        if isinstance(est, bool) or not isinstance(est, int) or not 0 <= est <= 100:
            raise JudgeError(E_SCHEMA, f"{judge}: estimate {est!r} is not an integer 0-100")
        unknown = [c for c in cited if c not in dossier.observation_ids]
        if unknown:
            raise JudgeError(
                E_SCHEMA, f"{judge}: cited observations not in the dossier: {unknown}"
            )
        if not cited:
            raise JudgeError(
                E_CITES_NOTHING,
                f"{judge}: scored {est} while citing no observation from the dossier",
            )
        if not any(c in rationale for c in cited):
            raise JudgeError(
                E_CITES_NOTHING,
                f"{judge}: the rationale names none of the observations it lists",
            )
    else:
        if est is not None:
            raise JudgeError(E_SCHEMA, f"{judge}: unscored but carries an estimate")
        if not obj.get("missingness_reason"):
            raise JudgeError(E_SCHEMA, f"{judge}: unscored with no missingness_reason")

    return JudgeVerdict(
        judge=judge, scored=scored, estimate=est, band=obj.get("band"),
        rationale=rationale, evidence_ids=cited, support=obj.get("support") or {},
        missingness_reason=obj.get("missingness_reason"),
        telemetry=telemetry, raw_path=raw_path,
    )


def score_dossier(
    dossier: Dossier,
    judges: Sequence[Judge],
    contract: GradingContract,
    rubric_text: str,
    schema_text: str,
    budget: Budget,
    raw_dir: Path,
    timeout: int = 600,
) -> tuple[StandingEstimate | None, list[JudgeVerdict], list[dict]]:
    """Returns (estimate, verdicts, failures)."""
    if dossier.is_empty:
        # An empty dossier needs no model call. The dossier builder already
        # knows there is nothing to weigh, and stress case S5 confirmed both
        # judges return unscored on one. Paying to re-learn that would spend
        # quota to produce a value this function can state itself.
        return (
            StandingEstimate(
                estimate_id=stable_id("se", dossier.person_id, dossier.period),
                person_id=dossier.person_id, periods=(dossier.period,),
                estimate=None, rubric_version=contract.rubric_version,
                contract_id=contract.contract_id, judges={}, reducer="short_circuit",
                evidence_ids=(), support=None, rationale="",
                missingness_reason=MissingnessReason.NO_OBSERVATIONS,
            ),
            [],
            [],
        )

    prompt = build_prompt(dossier, rubric_text, schema_text)
    raw_dir.mkdir(parents=True, exist_ok=True)
    verdicts: list[JudgeVerdict] = []
    failures: list[dict] = []

    for judge in judges:
        label = f"{dossier.dossier_id}/{judge.name}"
        try:
            budget.spend_call(label)          # cap halts BEFORE the call
        except BudgetExhausted:
            budget.remaining_work.append(label)
            raise
        raw_path = raw_dir / f"{dossier.dossier_id}__{judge.name}.txt"
        try:
            result = judge(prompt, timeout)
        except JudgeError as exc:
            failures.append({"dossier": dossier.dossier_id, "judge": judge.name,
                             "error_type": exc.error_type, "detail": exc.detail})
            continue
        raw_path.write_text(result.text)      # persist BEFORE parsing
        try:
            verdicts.append(
                parse_verdict(result.text, dossier, judge.name, result.telemetry,
                              str(raw_path))
            )
        except JudgeError as exc:
            failures.append({"dossier": dossier.dossier_id, "judge": judge.name,
                             "error_type": exc.error_type, "detail": exc.detail})

    if not verdicts:
        return None, verdicts, failures

    scored = [v for v in verdicts if v.scored]
    if not scored:
        reasons = {v.missingness_reason for v in verdicts}
        est = StandingEstimate(
            estimate_id=stable_id("se", dossier.person_id, dossier.period),
            person_id=dossier.person_id, periods=(dossier.period,), estimate=None,
            rubric_version=contract.rubric_version, contract_id=contract.contract_id,
            judges={}, reducer="mean_of_2", evidence_ids=(), support=None, rationale="",
            missingness_reason=MissingnessReason(sorted(reasons)[0]),
        )
        return est, verdicts, failures

    scores = {v.judge: float(v.estimate) for v in scored}
    value, needs_adjudication = reduce_judges(scores)
    gap = max(scores.values()) - min(scores.values()) if len(scores) > 1 else None
    evidence = tuple(sorted({e for v in scored for e in v.evidence_ids}))
    first = scored[0].support

    est = StandingEstimate(
        estimate_id=stable_id("se", dossier.person_id, dossier.period),
        person_id=dossier.person_id,
        periods=(dossier.period,),
        estimate=value,
        rubric_version=contract.rubric_version,
        contract_id=contract.contract_id,
        judges=scores,
        reducer=f"mean_of_{len(scores)}",
        evidence_ids=evidence,
        support=Support(
            distinct_original_sources=dossier.distinct_original_sources,
            distinct_publishers=dossier.distinct_publishers,
            reliability=first.get("reliability", "unknown"),
            specificity=first.get("specificity", "unknown"),
            contemporaneity=first.get("contemporaneity", "unknown"),
            across_judges_gap=gap,
            source_disagreement=first.get("source_disagreement"),
            periods_with_evidence=1,
            periods_needed=1,
        ),
        rationale="\n\n".join(f"[{v.judge}] {v.rationale}" for v in scored),
        needs_adjudication=needs_adjudication,
    )
    return est, verdicts, failures
