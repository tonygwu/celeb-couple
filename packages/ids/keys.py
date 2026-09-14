"""Canonical identifiers, unordered pair keys, and content hashes.

A pair key must be identical whichever way round the pair is named, or the
same couple enters the corpus twice and the mirrored-gap invariant breaks.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

__all__ = ["pair_key", "json_sha256", "content_sha256", "contract_id", "stable_id"]


def pair_key(a: str, b: str) -> str:
    """An order-independent key for an unordered pair of person ids."""
    if a == b:
        raise ValueError(f"a pairing needs two different people, got {a!r} twice")
    lo, hi = sorted((a, b))
    return f"{lo}|{hi}"


def json_sha256(obj: Any) -> str:
    """Hash a JSON-serialisable object canonically.

    sort_keys and tight separators, so two structurally identical objects hash
    the same regardless of how they were built.
    """
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def content_sha256(data: bytes) -> str:
    """Hash retrieved bytes exactly as retrieved."""
    return hashlib.sha256(data).hexdigest()


def contract_id(*parts: bytes) -> str:
    """Identify exactly the bytes a model was shown.

    Hash the concatenation of every file that reaches the judge -- the rubric
    and the output schema -- and nothing else. A file that cannot move a score
    is deliberately excluded, so an editorial change to a README does not
    invalidate a corpus.

    A contract id says WHAT WAS SENT. It does not make a fresh invocation of
    the same model against the same bytes deterministic, and nothing in this
    codebase claims it does. Reproducibility comes from replaying the stored
    responses.
    """
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.hexdigest()[:12]


def stable_id(prefix: str, *parts: str) -> str:
    """A content-derived id that survives re-retrieval of the same thing."""
    digest = hashlib.sha256("\n".join(parts).encode()).hexdigest()[:12]
    return f"{prefix}_{digest}"
