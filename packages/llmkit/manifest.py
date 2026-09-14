"""A persisted record of what a stage actually did.

WHY THIS EXISTS
---------------
verbatim-index persists a run manifest for its predictions pipeline and NOT for
its main one, which prints the same reconciliation to stdout and loses it. This
project would have inherited that gap: three of its scripts already spend model
quota and none of them left a durable record of the run.

THE RECONCILIATION IS ENFORCED, NOT REPORTED
--------------------------------------------
``attempted == succeeded + cached + excluded + failed`` is checked, and a
mismatch raises. A record being dropped or double-counted between two stages is
exactly the kind of quiet wrong answer that makes every downstream number
unreadable, and a bare count would hide it.

Progress is never a completion count. Every stage carries an error taxonomy,
because a fully broken component reads as "slow" otherwise.
"""

from __future__ import annotations

import json
import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from packages.llmkit.taxonomy import ALL_ERROR_TYPES

__all__ = ["StageSummary", "RunManifest", "ReconciliationError", "git_revision"]


class ReconciliationError(RuntimeError):
    pass


def git_revision(repo: Path) -> str | None:
    """The commit the code was at. None when that cannot be read."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or None if out.returncode == 0 else None
    except Exception:
        return None


@dataclass
class StageSummary:
    stage: str
    attempted: int = 0
    succeeded: int = 0
    cached: int = 0
    excluded: int = 0
    failed: int = 0
    error_taxonomy: dict[str, int] = field(default_factory=dict)
    notes: dict = field(default_factory=dict)

    def record_failure(self, error_type: str) -> None:
        if error_type not in ALL_ERROR_TYPES:
            raise ValueError(
                f"{error_type!r} is not in ALL_ERROR_TYPES. Add it there rather "
                "than inventing a label at the call site: an inline subset is how "
                "nine load-shedding failures once got relabelled as crashes."
            )
        self.failed += 1
        self.error_taxonomy[error_type] = self.error_taxonomy.get(error_type, 0) + 1

    def reconcile(self) -> None:
        total = self.succeeded + self.cached + self.excluded + self.failed
        if total != self.attempted:
            raise ReconciliationError(
                f"stage {self.stage!r}: attempted {self.attempted} but "
                f"succeeded {self.succeeded} + cached {self.cached} + excluded "
                f"{self.excluded} + failed {self.failed} = {total}. A record is "
                "being dropped or double-counted."
            )

    def as_dict(self) -> dict:
        self.reconcile()
        return {
            "stage": self.stage, "attempted": self.attempted,
            "succeeded": self.succeeded, "cached": self.cached,
            "excluded": self.excluded, "failed": self.failed,
            "error_taxonomy": dict(self.error_taxonomy), "notes": dict(self.notes),
        }


@dataclass
class RunManifest:
    """One manifest per invocation, written atomically at the end."""

    stage_name: str
    repo: Path
    args: dict
    contracts: dict = field(default_factory=dict)
    billing: str = "subscription-only"
    caps: dict = field(default_factory=dict)
    summaries: list[StageSummary] = field(default_factory=list)
    run_id: str = ""
    started_at_utc: str = ""
    finished_at_utc: str = ""
    code_revision: str | None = None
    halted: bool = False
    halt_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            self.run_id = f"{stamp}-{self.stage_name}-{uuid.uuid4().hex[:8]}"
        if not self.started_at_utc:
            # UTC from the clock, never from a file mtime and never local time
            self.started_at_utc = datetime.now(timezone.utc).isoformat()
        if self.code_revision is None:
            self.code_revision = git_revision(self.repo)

    def stage(self, name: str) -> StageSummary:
        s = StageSummary(stage=name)
        self.summaries.append(s)
        return s

    def halt(self, reason: str) -> None:
        """A halt is reported as a halt, with what was left unreached."""
        self.halted = True
        self.halt_reason = reason

    def as_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "stage_name": self.stage_name,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc
            or datetime.now(timezone.utc).isoformat(),
            "code_revision": self.code_revision,
            "billing": self.billing,
            "caps": dict(self.caps),
            "args": dict(self.args),
            "contracts": dict(self.contracts),
            "halted": self.halted,
            "halt_reason": self.halt_reason,
            "summaries": [s.as_dict() for s in self.summaries],
        }

    def write(self, out_dir: Path) -> Path:
        self.finished_at_utc = datetime.now(timezone.utc).isoformat()
        # Serialise BEFORE touching the filesystem. as_dict() reconciles every
        # stage and raises on a mismatch, and doing it inside the open() left a
        # ZERO-BYTE .tmp behind -- which is the worst possible record of a
        # failure, because it reads as a stray file rather than a lost
        # manifest. One sat in data/pilot/manifests/ for hours.
        payload = self.as_dict()
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.run_id}.json"
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w") as fh:
            json.dump(payload, fh, indent=2, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())   # the rename orders only against flushed data
        os.replace(tmp, path)
        return path
