"""Parse one person-period verdict, and cache it.

A person-period score is asked for ONCE and reused everywhere that person-year
appears. That is the point of the cache and it is a correctness fix before it is
a cost one: the film-by-film rubric it replaces gave the same person in the same
year 9.0 for one film and 9.5 for another -- a judge disagreeing with itself by
more than two model families disagree with each other.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

__all__ = ["PersonVerdict", "ParseError", "parse_person_verdict",
           "person_period_id", "cache_key"]


class ParseError(RuntimeError):
    pass


@dataclass(frozen=True)
class PersonVerdict:
    person_period_id: str
    judged: bool
    score: float | None
    evidence_used: bool | None
    evidence_ids: tuple[str, ...]
    reasoning: str
    cannot_judge_reason: str | None


def person_period_id(qid: str, period: str) -> str:
    return f"pp_{qid}_{period}"


def cache_key(qid: str, period: str, family: str) -> str:
    """One cache entry per person, year AND judge family.

    Families are separate populations with their own scales -- fable's mean sits
    about 0.2 below astra's -- so pooling them into one cached number would
    average two rulers and report the result as a reading.
    """
    return f"{family}:{person_period_id(qid, period)}"


def _first_json_object(text: str) -> dict:
    """The judge sometimes wraps its JSON in prose or a fenced block.

    One of the two families fences every response. A bare `json.loads` reads
    190 of 262 stored files, raises nothing, and reports a corpus a third short
    -- measured twice in this project, once in a throwaway script that then
    produced plausible wrong numbers.
    """
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ParseError("no JSON object in the response")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise ParseError(f"response is not valid JSON: {exc}") from exc


def parse_person_verdict(text: str, ppid: str) -> PersonVerdict:
    obj = _first_json_object(text)
    if obj.get("schema_version") != "person-1.0":
        raise ParseError(f"schema_version is {obj.get('schema_version')!r}")
    if obj.get("person_period_id") != ppid:
        raise ParseError(
            f"verdict is for {obj.get('person_period_id')!r}, not {ppid!r}")

    judged = obj.get("judged")
    if not isinstance(judged, bool):
        raise ParseError(f"judged is {judged!r}, not a boolean")
    reasoning = (obj.get("reasoning") or "").strip()
    if not reasoning:
        raise ParseError("reasoning is empty")

    score = obj.get("score")
    if score is not None:
        # `isinstance(True, int)` is True in Python, so a bare `"score": true`
        # would become 1.0 -- a real score, indistinguishable in the artifact
        # from one the judge meant. Both sibling parsers were bitten by this.
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise ParseError(f"score is {score!r}, which is not a number")
        score = float(score)
        if not 0 <= score <= 10:
            raise ParseError(f"score {score} is outside 0..10")

    if not judged:
        if score is not None:
            raise ParseError("not judged, but a score was returned")
        if not obj.get("cannot_judge_reason"):
            raise ParseError("not judged, with no cannot_judge_reason")
        return PersonVerdict(ppid, False, None, None, (), reasoning,
                             obj.get("cannot_judge_reason"))
    if score is None:
        raise ParseError("judged, but no score")

    ids = obj.get("evidence_ids") or []
    if not isinstance(ids, list) or any(not isinstance(x, str) for x in ids):
        raise ParseError(f"evidence_ids is {ids!r}, not a list of strings")
    used = obj.get("evidence_used")
    if used and not ids:
        raise ParseError("evidence_used is true but no evidence_ids were cited")
    return PersonVerdict(ppid, True, score, bool(used), tuple(ids), reasoning, None)
