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

__all__ = ["ClobberRefused", "guard_output"]


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
