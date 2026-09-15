"""Parse and validate one pairing verdict.

The GAP is the primary output and everything here treats it that way. The two
absolute scores are secondary and are checked for CONSISTENCY with the gap
rather than trusted on their own: a judge that returns gap +0.4 alongside
absolutes that differ by -1.2 has contradicted itself, and neither number can
then be used.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

__all__ = ["PairingVerdict", "ParseError", "parse_pairing_verdict",
           "ABSOLUTE_TOLERANCE"]

#: How far the two absolute scores may drift from the stated gap before the
#: verdict is treated as self-contradictory.
#:
#: 0.15 rather than 0.0 because the judge rounds: absolutes given to one decimal
#: can differ from a gap given to one decimal by a rounding step without either
#: being wrong. Wider than that is a real contradiction.
ABSOLUTE_TOLERANCE = 0.15


class ParseError(RuntimeError):
    pass


@dataclass(frozen=True)
class PairingVerdict:
    pairing_id: str
    judged: bool
    gap: float | None
    f_absolute: float | None
    m_absolute: float | None
    centrality: float | None
    reasoning: str
    cannot_judge_reason: str | None
    raw: str


def _first_json_object(text: str) -> dict:
    """The judge sometimes wraps its JSON in prose or a fenced block."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        raise ParseError("no JSON object in the response")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise ParseError(f"response is not valid JSON: {exc}") from exc


def _number(obj: dict, key: str) -> float | None:
    v = obj.get(key)
    if v is None:
        return None
    # `isinstance(True, int)` is True in Python, so a bare `"gap": true` would
    # otherwise become the value 1.0 -- a real gap, indistinguishable in the
    # artifact from one the judge meant. The sibling parser was bitten by
    # exactly this on `estimate`.
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ParseError(f"{key} is {v!r}, which is not a number")
    return float(v)


def parse_pairing_verdict(text: str, pairing_id: str) -> PairingVerdict:
    obj = _first_json_object(text)

    if obj.get("schema_version") != "pairing-1.0":
        raise ParseError(f"schema_version is {obj.get('schema_version')!r}")
    if obj.get("pairing_id") != pairing_id:
        raise ParseError(
            f"verdict is for pairing {obj.get('pairing_id')!r}, not {pairing_id!r}")

    judged = obj.get("judged")
    if not isinstance(judged, bool):
        raise ParseError(f"judged is {judged!r}, not a boolean")

    reasoning = (obj.get("reasoning") or "").strip()
    if not reasoning:
        raise ParseError("reasoning is empty")

    gap = _number(obj, "gap")
    fa, ma = _number(obj, "f_absolute"), _number(obj, "m_absolute")
    cen = _number(obj, "centrality")

    if not judged:
        if gap is not None:
            raise ParseError("not judged, but a gap was returned")
        if not obj.get("cannot_judge_reason"):
            raise ParseError("not judged, with no cannot_judge_reason")
        return PairingVerdict(pairing_id, False, None, None, None, None,
                              reasoning, obj.get("cannot_judge_reason"), text)

    if gap is None:
        raise ParseError("judged, but no gap")
    if not -10 <= gap <= 10:
        raise ParseError(f"gap {gap} is outside -10..10")
    for name, v in (("f_absolute", fa), ("m_absolute", ma)):
        if v is not None and not 0 <= v <= 10:
            raise ParseError(f"{name} {v} is outside 0..10")
    if cen is not None and not 0 <= cen <= 1:
        raise ParseError(f"centrality {cen} is outside 0..1")

    # The consistency check the docstring promises. Only possible when both
    # absolutes are present; they are optional and secondary by design.
    if fa is not None and ma is not None:
        implied = fa - ma
        if abs(implied - gap) > ABSOLUTE_TOLERANCE:
            raise ParseError(
                f"self-contradictory: gap {gap:+g} but f_absolute - m_absolute "
                f"= {implied:+g}. The absolutes must agree with the gap.")

    return PairingVerdict(pairing_id, True, gap, fa, ma, cen, reasoning, None, text)
