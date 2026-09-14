"""Refuse to replace a richer artifact with a poorer one.

A `--repeats 1` smoke test overwrote a real four-repeat rater-noise measurement
tonight, destroying eight model calls' worth of work to check a string format.
The write succeeded, exited zero, and said nothing.

The guard is deliberately narrow. It compares ONE declared quality field and
refuses only when the incoming value is strictly lower, because a guard that
tries to judge overall richness will eventually block a legitimate write and
teach everyone to pass --force by reflex.
"""

from __future__ import annotations

import json
from pathlib import Path

__all__ = ["ClobberRefused", "guard_output", "archive_previous"]


class ClobberRefused(SystemExit):
    pass


def guard_output(path: Path, *, field: str, value, force: bool = False) -> None:
    """Refuse to overwrite when the existing artifact scores higher on ``field``.

    ``field`` is a top-level key whose value orders "richer". Missing file,
    missing field, unorderable values, or ``force`` all allow the write.
    """
    if force or not path.exists():
        return
    try:
        existing = json.loads(path.read_text()).get(field)
    except (json.JSONDecodeError, OSError):
        return          # an unreadable artifact is not worth protecting
    if existing is None:
        return
    try:
        poorer = value < existing
    except TypeError:
        return          # not comparable; the caller chose a bad field, not our call
    if poorer:
        raise ClobberRefused(
            f"\nRefusing to overwrite {path.name}.\n"
            f"  It holds {field}={existing}; this run has {field}={value}.\n"
            f"  A smaller run replacing a larger one destroys the measurement "
            f"and exits zero, which is how a --repeats 1 smoke test wiped a\n"
            f"  four-repeat result tonight.\n"
            f"  Write elsewhere with --out, or pass --force if you mean it.\n"
        )


def archive_previous(path: Path) -> Path | None:
    """Keep a copy of ``path``'s current contents before it is overwritten.

    Returns the archived path, or ``None`` when there was nothing to keep.

    `guard_output` refuses to replace a RICHER artifact with a poorer one. It
    says nothing about an equally rich replacement, which is the ordinary case
    for a re-score and the one that silently loses the previous estimates. That
    loss is why the run-to-run stability measurement rests on three rows that
    happened to overlap between two corpora rather than on the whole corpus.

    The copy is content-addressed, so re-running a stage that produces the same
    answer does not grow the history. The original is left in place: this runs
    BEFORE the new write, and moving it would lose the artifact entirely if
    that write then failed.
    """
    import hashlib
    import shutil

    if not path.exists():
        return None
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()[:12]
    history = path.parent / "history"
    history.mkdir(parents=True, exist_ok=True)
    dest = history / f"{path.stem}-{digest}{path.suffix}"
    if not dest.exists():
        shutil.copy2(path, dest)
    return dest
