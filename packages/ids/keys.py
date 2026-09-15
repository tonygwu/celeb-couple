"""Canonical identifiers, unordered pair keys, and content hashes.

A pair key must be identical whichever way round the pair is named, or the
same couple enters the corpus twice and the mirrored-gap invariant breaks.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

__all__ = ["pair_key", "json_sha256", "content_sha256", "contract_id",
           "CONTRACT_ID_SCHEME", "stable_id"]

#: How ``contract_id`` combines its parts. Stamped into every artifact beside
#: the id, because a scheme change moves the id without any rubric byte
#: moving, and those two cases must not look alike afterwards.
CONTRACT_ID_SCHEME = "v2-length-prefixed"


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

    BOUNDARY AMBIGUITY, FIXED 2026-09-14 (scheme v2). The parts used to be
    concatenated with no separator, so moving text from the end of the rubric
    to the start of the schema left the id unchanged. That is a plausible
    refactor rather than a contrived one, and it would have let two different
    contracts share an id.

    Each part is now length-prefixed with its byte count, so a byte moved
    across the boundary changes both lengths and therefore the id. The prefix
    is the decimal length and a newline, hashed as ASCII.

    This CHANGED EVERY ID. The corpus previously recorded standing
    `ab015c99ad3e`, mentions `875ec6ad847e` and romance `7f82adbc0c79`; none of
    those ids is produced by this function any more. That is why the fix waited
    for a rubric version bump, and why it landed in the same commit as one.

    A scheme change is not a rubric change: romance-1.0's bytes did not move
    even though its id did. ``CONTRACT_ID_SCHEME`` is stamped alongside the id
    in every artifact so a reader can tell those two cases apart.
    """
    h = hashlib.sha256()
    for p in parts:
        h.update(f"{len(p)}\n".encode("ascii"))
        h.update(p)
    return h.hexdigest()[:12]


#: What ``stable_id`` joins its parts with before hashing.
_ID_SEPARATOR = "\n"


def stable_id(prefix: str, *parts: str) -> str:
    """A content-derived id that survives re-retrieval of the same thing.

    The parts are joined and hashed, so a part CONTAINING the separator makes
    the join ambiguous: ("A\nB", "C") and ("A", "B\nC") produce the same id,
    and two different things would silently share an identifier.

    Most parts are internal -- Wikidata ids, periods, ranks -- but
    ``scripts/extract_prose_mentions.py`` builds a mention id from ``publisher``
    and ``list_name``, both taken straight from a model's JSON output, where a
    newline is an ordinary thing to emit.

    A separator in a part is REFUSED rather than escaped, and the hash is left
    alone. Changing the join would renumber every observation id, and the
    stored rationales cite those ids by name, so the whole corpus's grounding
    would fail and only a re-score could repair it. No current input contains a
    newline, so refusing costs nothing and closes the hole.
    """
    for i, part in enumerate(parts):
        if _ID_SEPARATOR in part:
            raise ValueError(
                f"stable_id part {i} contains the separator used to join them, "
                f"which makes the id ambiguous: {part!r}. Strip or replace it "
                "before building an id."
            )
    digest = hashlib.sha256(_ID_SEPARATOR.join(parts).encode()).hexdigest()[:12]
    return f"{prefix}_{digest}"
