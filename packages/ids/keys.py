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

    KNOWN BOUNDARY AMBIGUITY, deliberately not fixed here. The parts are
    concatenated with no separator, so moving text from the end of the rubric
    to the start of the schema leaves the id unchanged. That is a plausible
    refactor rather than a contrived one.

    It is not fixed because fixing it changes the id. The corpus records
    contract `ab015c99ad3e`, the plan forbids pooling estimates across contract
    ids, and a length-prefixed hash would make every existing estimate look
    like it came from a different contract -- for a risk that requires a very
    specific edit to realise. The right moment is the next rubric version bump,
    when the id changes anyway. Filed in docs/BACKLOG.md.
    """
    h = hashlib.sha256()
    for p in parts:
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
