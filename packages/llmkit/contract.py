"""The grading contract: exactly the bytes a judge is shown.

Hash the rubric and the output schema and nothing else, because only those two
files can move a score.  Stamp the id on every record.  Refuse to pool
estimates produced under different ids -- scores from different rubrics are not
comparable and averaging them hides that.

A contract id says WHAT WAS SENT.  It does not make a fresh invocation of the
same model deterministic.  Reproducibility comes from replaying stored
responses, and nothing here pretends otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from packages.ids.keys import contract_id

__all__ = ["GradingContract", "load_contract", "MixedContractError",
           "refuse_mixed_contracts"]


class MixedContractError(RuntimeError):
    pass


@dataclass(frozen=True)
class GradingContract:
    contract_id: str
    rubric_sha256: str
    schema_sha256: str
    rubric_bytes: int
    schema_bytes: int
    rubric_version: str

    def as_dict(self) -> dict:
        return {
            "contract_id": self.contract_id,
            "rubric_sha256": self.rubric_sha256,
            "schema_sha256": self.schema_sha256,
            "rubric_bytes": self.rubric_bytes,
            "schema_bytes": self.schema_bytes,
            "rubric_version": self.rubric_version,
        }


def load_contract(rubric_path: Path, schema_path: Path, rubric_version: str) -> GradingContract:
    import hashlib

    rb = rubric_path.read_bytes()
    sb = schema_path.read_bytes()
    return GradingContract(
        contract_id=contract_id(rb, sb),
        rubric_sha256=hashlib.sha256(rb).hexdigest(),
        schema_sha256=hashlib.sha256(sb).hexdigest(),
        rubric_bytes=len(rb),
        schema_bytes=len(sb),
        rubric_version=rubric_version,
    )


def refuse_mixed_contracts(records: list[dict]) -> None:
    """Stop rather than average scores produced under different rubrics.

    A record with NO contract_id counts as its own unknown version rather than
    being skipped. The filter used to drop them, so a set that was half
    contract A and half unlabelled passed a check whose entire purpose is
    knowing which rubric produced a number. Unknown provenance is the thing
    this refuses, not an exemption from it.
    """
    ids = {r.get("contract_id") or "<no contract_id>" for r in records}
    if len(ids) > 1:
        raise MixedContractError(
            f"REFUSING TO POOL: estimates span {len(ids)} contract versions "
            f"({sorted(ids)}). Scores from different rubrics are not "
            f"comparable, and a record with no contract_id has unknown "
            f"provenance rather than a matching one."
        )
