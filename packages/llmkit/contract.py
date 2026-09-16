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

from packages.ids.keys import CONTRACT_ID_SCHEME, contract_id

__all__ = ["GradingContract", "load_contract", "MixedContractError",
           "refuse_mixed_contracts", "StaleContractError",
           "current_contract_ids", "refuse_stale_contract",
           "STANDING_RUBRIC_VERSION", "MENTIONS_RUBRIC_VERSION",
           "ROMANCE_RUBRIC_VERSION", "PAIRING_RUBRIC_VERSION",
           "PERSON_RUBRIC_VERSION", "COUPLES_RUBRIC_VERSION"]

#: The rubric version strings, in ONE place.
#:
#: They used to be typed as a literal at each call site -- five of them for the
#: standing rubric alone. docs/CONTRACT-BUMP.md says the worst outcome of a bump
#: is "a changed contract with an unchanged version string", because the
#: artifacts then disagree about which rubric they used, and five hand-edits is
#: exactly how one gets missed. tests/test_rubric_version_single_source.py fails
#: if a script types one of these again.
#:
#: Bump a version when the rubric or schema BYTES change. Do not bump it when
#: only the hashing scheme changed: that moves the contract id without moving a
#: rubric byte, and ``CONTRACT_ID_SCHEME`` records it instead. romance-1.0 is
#: the live example -- its id changed on 2026-09-14 and its bytes did not.
STANDING_RUBRIC_VERSION = "standing-rubric-2.1"
MENTIONS_RUBRIC_VERSION = "mentions-1.1"
ROMANCE_RUBRIC_VERSION = "romance-1.0"
PAIRING_RUBRIC_VERSION = "pairing-1.0"
PERSON_RUBRIC_VERSION = "person-1.0"
COUPLES_RUBRIC_VERSION = "couples-1.0"


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
            "contract_id_scheme": CONTRACT_ID_SCHEME,
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


class StaleContractError(SystemExit):
    """Exits with a message, like MissingArtifact in the sibling module.

    A SystemExit rather than a RuntimeError because this is reached from
    script entrypoints, where a traceback tells the operator less than a
    sentence does.
    """


def current_contract_ids(repo: Path) -> dict[str, str]:
    """Every contract id the rubrics ON DISK currently produce, id -> name.

    Derived by globbing ``rubrics/*/`` rather than listing the three known
    rubrics, so adding a fourth needs no code change. This repository has been
    bitten twice by code that enumerated a set which later grew.

    A directory without exactly one ``.md`` and one ``.schema.json`` is
    SKIPPED, not guessed at. Which two files reach the judge is the whole
    definition of the contract, and picking one of several candidates would
    compute an id for bytes nobody was shown.
    """
    ids: dict[str, str] = {}
    root = repo / "rubrics"
    if not root.is_dir():
        return ids
    for d in sorted(root.iterdir()):
        if not d.is_dir():
            continue
        md = sorted(d.glob("*.md"))
        schema = sorted(d.glob("*.schema.json"))
        if len(md) != 1 or len(schema) != 1:
            continue
        ids[contract_id(md[0].read_bytes(), schema[0].read_bytes())] = d.name
    return ids


def refuse_stale_contract(repo: Path, artifact: str, data: dict) -> None:
    """Refuse an artifact scored under a rubric that no longer exists on disk.

    THE HAZARD. The grading contract is sha256(rubric + schema), so a one-line
    typo fix in a rubric gives a new contract_id and every stored estimate now
    came from a rubric that is gone. Nothing detected that. The scores stayed
    on disk, the analysis scripts kept reading them, and every report kept
    presenting them as current -- a quiet wrong answer of exactly the shape
    this project exists to avoid, and one that gets likelier the moment
    somebody acts on docs/BACKLOG.md's three filed rubric corrections.

    Why this lives inside ``require`` rather than in each analysis script:
    ``refuse_mixed_contracts`` was written as a safety function and left with
    no production caller for weeks. A guard that every consumer must remember
    to invoke is a guard that a new script silently opts out of. Nine scripts
    read scored artifacts and none of them has to know this exists.

    An artifact with no ``contract`` block is not checked, because most
    artifacts are arithmetic over records and no rubric produced them. A repo
    with no ``rubrics/`` directory is not checked either, which is how test
    fixtures and scratch directories pass.
    """
    stored = data.get("contract")
    if not isinstance(stored, dict) or not stored.get("contract_id"):
        return
    # An artifact whose run invoked NO judge has no estimate for a rubric to
    # have produced, so its contract block records which bytes WOULD have been
    # sent rather than which produced a number. Refusing it is a false
    # positive, and it fired as one: data/pilot/run/pilot_report.json records
    # sent_to_judges 0, scored 0, calls_made 0 on both judges and zero
    # dossiers -- every dossier was empty and short-circuited before any judge
    # ran -- yet it blocked the entire report pass after a rubric bump.
    #
    # This is the same principle the docstring above already states for an
    # artifact with no contract block at all. That one happens to carry one.
    budgets = data.get("budgets")
    if (isinstance(budgets, dict) and budgets
            and all(isinstance(b, dict) and b.get("calls_made") == 0
                    for b in budgets.values())):
        return
    ids = current_contract_ids(repo)
    if not ids or stored["contract_id"] in ids:
        return
    raise StaleContractError(
        f"\nSTALE CONTRACT: {artifact}\n"
        f"  It was scored under contract {stored['contract_id']} "
        f"(rubric_version {stored.get('rubric_version', 'unknown')}), and no "
        f"rubric on disk produces that id any more.\n"
        f"  Rubrics present now: "
        + ", ".join(f"{name} -> {cid}" for cid, name in sorted(ids.items(),
                                                               key=lambda kv: kv[1]))
        + "\n"
        f"  Estimates from different rubrics must not be pooled or reported "
        f"together, so this artifact cannot be read as current.\n"
        f"  Either restore the rubric these scores were produced under, or "
        f"re-score against the new one. See docs/CONTRACT-BUMP.md.\n"
    )
