"""Identifying which characters in a film are a couple.

Pure functions only: prompt construction, verdict parsing, and the board
filter. Everything here is testable without spending a call.

WEIGHT AND CONFIDENCE ARE DIFFERENT AXES and the split is the point of this
module. `confidence` says how sure the judge is that the relationship exists.
`weight` says how much of the film it is. Alec Baldwin's Jeff King really is
Anna Scott's boyfriend in Notting Hill, so confidence is high, and he has one
scene, so weight is incidental. A filter on confidence alone let that pair onto
the board, which is what this split fixes.
"""
from __future__ import annotations

import json
import re

#: Weights whose pairs become board rows. `incidental` is recorded and
#: excluded, never dropped silently, so the exclusion stays countable.
BOARD_WEIGHTS = ("central", "substantial")
WEIGHTS = ("central", "substantial", "incidental")
CONFIDENCES = ("high", "medium", "low")


class CoupleVerdictError(ValueError):
    """The judge's reply could not be read as a couples verdict."""


def cache_key(tconst: str, family: str) -> str:
    """One entry per (film, judge family).

    Family-keyed for the same reason the person cache is: two families are two
    populations, and pooling them would hide disagreement rather than measure it.
    """
    return f"{tconst}|{family}"


def build_prompt(title: str, year: int, cast: list[tuple], rubric: str,
                 name_of: dict[str, str]) -> str:
    """`cast` is (ordering, nconst, category, characters), lowest ordering first."""
    if not title:
        raise ValueError("refusing to build a prompt with no film title")
    roster = "\n".join(
        f"  - {name_of.get(n, n)} as {ch or '?'}" for _, n, _, ch in sorted(cast)
    ) or "  (IMDb lists no billed actors for this film)"
    return (
        f"{rubric}\n\n"
        f"FILM: {title} ({year})\n"
        f"Billed cast IMDb lists for it:\n{roster}\n\n"
        "Reply with ONLY a JSON object of this shape:\n"
        '{"pairs": [{"a": "<actor name>", "b": "<actor name>", '
        '"characters": "<char A> and <char B>", '
        '"weight": "central"|"substantial"|"incidental", '
        '"in_billed_list": true|false, '
        '"confidence": "high"|"medium"|"low"}], "note": "<one sentence, or empty>"}\n'
    )


def _first_json_object(text: str) -> str:
    """Recover the first balanced {...} run.

    One family fences its JSON in markdown and the other does not, and a bare
    json.loads on the whole reply read 190 of 262 files once while looking
    like it had read them all.
    """
    depth = start = 0
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise CoupleVerdictError("no balanced JSON object in the reply")


def parse_couples_verdict(text: str) -> dict:
    """Parse and VALIDATE. A bad enum raises rather than defaulting.

    Defaulting an unreadable weight to `incidental` would silently delete board
    rows, and defaulting it to `central` would silently invent them. Both are
    worse than a loud failure on one film.
    """
    try:
        obj = json.loads(_first_json_object(text))
    except json.JSONDecodeError as exc:
        raise CoupleVerdictError(f"reply is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict) or "pairs" not in obj:
        raise CoupleVerdictError("reply has no `pairs` key")
    pairs = obj["pairs"]
    if not isinstance(pairs, list):
        raise CoupleVerdictError("`pairs` is not a list")
    for i, p in enumerate(pairs):
        if not isinstance(p, dict):
            raise CoupleVerdictError(f"pair {i} is not an object")
        for field in ("a", "b", "weight", "in_billed_list", "confidence"):
            if field not in p:
                raise CoupleVerdictError(f"pair {i} has no `{field}`")
        if p["weight"] not in WEIGHTS:
            raise CoupleVerdictError(f"pair {i} weight {p['weight']!r} is not one of {WEIGHTS}")
        if p["confidence"] not in CONFIDENCES:
            raise CoupleVerdictError(
                f"pair {i} confidence {p['confidence']!r} is not one of {CONFIDENCES}")
        if not isinstance(p["in_billed_list"], bool):
            raise CoupleVerdictError(f"pair {i} in_billed_list is not a boolean")
        if not str(p["a"]).strip() or not str(p["b"]).strip():
            raise CoupleVerdictError(f"pair {i} names an empty actor")
        if str(p["a"]).strip().casefold() == str(p["b"]).strip().casefold():
            raise CoupleVerdictError(f"pair {i} pairs {p['a']!r} with themselves")
    return {"pairs": pairs, "note": obj.get("note", "")}


def board_pairs(verdict: dict) -> list[dict]:
    """The pairs that become board rows. Weight decides, confidence does not."""
    return [p for p in verdict["pairs"] if p["weight"] in BOARD_WEIGHTS]


def excluded_pairs(verdict: dict) -> list[dict]:
    """The complement of `board_pairs`. Kept so exclusions stay countable."""
    return [p for p in verdict["pairs"] if p["weight"] not in BOARD_WEIGHTS]
