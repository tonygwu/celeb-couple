"""One canonical score per (person, year), averaged over every grading of it.

A person-year may now be graded several times, by several models. The operator's
rule, 2026-09-16: keep every grading, and make the canonical score their mean.

WHY THIS EXISTS. Fable was the binding constraint on the project: it has its own
weekly allowance, separate from the general pool, and it is the scarcest window
on every account. Measured on five person-years, Opus disagreed with Fable by a
mean of 0.18 while Fable disagreed with ITSELF by 0.12 on a re-run, and the
established cross-family floor between Fable and astra is 0.307. So Opus is
inside the noise and may grade the backlog. Sonnet measured 0.35 and failed 1 of
5 on schema, which is why `NOISY_MODELS` names it.

THREE THINGS THIS DELIBERATELY MAKES VISIBLE rather than smoothing away:

1. `n` -- a person-year averaged from four gradings is more precise than one
   averaged from one. Pooling them without saying so hides that.
2. `spread` -- max minus min across the gradings. This is the per-tuple
   disagreement, and it replaces the old cross-FAMILY error bar, which stopped
   being computable once families were pooled into one canonical number.
3. `models` -- which models produced it, so a later decision to drop one does
   not require re-grading anything.
"""
from __future__ import annotations

import statistics as st
from fractions import Fraction

#: What each family's runner actually invoked. The early cache entries predate
#: the `model` field, so the model has to be recovered from the family. These
#: are the pinned defaults the scripts used, not a guess.
MODEL_FOR_FAMILY = {
    "fable": "claude-fable-5-1",
    "astra": "gpt-6-astra",
    "opus": "claude-opus-5",
    "sonnet": "claude-sonnet-5",
}

#: Measured noisier than the cross-family floor. Kept in the average because
#: the operator asked for every grading to count, and tagged so the decision
#: stays reversible without re-grading.
NOISY_MODELS = ("claude-sonnet-5",)


class GradingError(ValueError):
    """A grading record is missing something the average depends on."""


def normalise_grading(entry: dict, *, source: str) -> dict:
    """One cache entry -> one grading record with full provenance.

    `graded_at_utc` is None for every pre-2026-09-16 entry, because those runs
    did not record it. It is NOT back-filled from file mtime: mtime says when a
    file was touched, not when the judgment was made, and this repository has
    already paid for that class of bug twice.
    """
    for field in ("person_id", "period", "family"):
        if field not in entry:
            raise GradingError(f"grading from {source} has no `{field}`")
    family = entry["family"]
    model = entry.get("model") or MODEL_FOR_FAMILY.get(family)
    if not model:
        raise GradingError(
            f"cannot name the model behind family {family!r} from {source}: "
            "add it to MODEL_FOR_FAMILY rather than letting it default")
    return {
        "person_id": entry["person_id"],
        "person": entry.get("person"),
        "period": str(entry["period"]),
        "family": family,
        "model": model,
        "judged": bool(entry.get("judged")),
        "score": entry.get("score"),
        "evidence_used": bool(entry.get("evidence_used")),
        "graded_at_utc": entry.get("graded_at_utc"),
        "graded_at_known": entry.get("graded_at_utc") is not None,
        "contract_id": (entry.get("contract") or {}).get("contract_id"),
        "source": source,
    }


def canonical_scores(gradings: list[dict], *, exclude_models: tuple = ()) -> dict:
    """(person_id, period) -> the canonical score and what it is made of.

    Only judged gradings with a score count. An unjudged grading is a refusal,
    not a zero, and averaging a refusal in as 0.0 would be the single most
    damaging silent-default available here.
    """
    buckets: dict[tuple[str, str], list[dict]] = {}
    for g in gradings:
        if not g["judged"] or g["score"] is None:
            continue
        if g["model"] in exclude_models:
            continue
        buckets.setdefault((g["person_id"], g["period"]), []).append(g)

    out = {}
    for key, gs in buckets.items():
        vals = [Fraction(str(g["score"])) for g in gs]
        mean = sum(vals) / len(vals)
        out[key] = {
            "score": float(mean),
            "n": len(gs),
            "spread": float(max(vals) - min(vals)),
            "models": sorted({g["model"] for g in gs}),
            "families": sorted({g["family"] for g in gs}),
            "any_evidence": any(g["evidence_used"] for g in gs),
            "contract_ids": sorted({g["contract_id"] for g in gs if g["contract_id"]}),
            "person": next((g["person"] for g in gs if g.get("person")), None),
            "noisy_included": sorted({g["model"] for g in gs} & set(NOISY_MODELS)),
        }
    return out


def refuse_pooled_contracts(canon: dict) -> None:
    """Averaging across grading contracts would pool two different questions."""
    bad = {k: v["contract_ids"] for k, v in canon.items() if len(v["contract_ids"]) > 1}
    if bad:
        raise GradingError(
            f"{len(bad)} person-years were graded under more than one contract, "
            f"so their gradings answer different questions and must not be "
            f"averaged. First: {next(iter(bad.items()))}")


def coverage(canon: dict) -> dict:
    """Progress as a taxonomy, never a bare count."""
    by_n: dict[int, int] = {}
    for v in canon.values():
        by_n[v["n"]] = by_n.get(v["n"], 0) + 1
    spreads = [v["spread"] for v in canon.values() if v["n"] > 1]
    return {
        "person_years": len(canon),
        "by_grading_count": dict(sorted(by_n.items())),
        "multiply_graded": sum(1 for v in canon.values() if v["n"] > 1),
        "mean_spread_where_multiple": (round(st.mean(spreads), 3) if spreads else None),
        "max_spread": (round(max(spreads), 3) if spreads else None),
    }
