"""Turn Wikidata relationship candidates into reviewable episodes.

Two rules do most of the work.

A dating-to-marriage progression is ONE episode, not two scoring opportunities.
Wikidata stores it as two statements -- an unmarried_partner span that ends on
the day a spouse span begins -- and both of the pilot cohort's longest
relationships arrive in exactly that shape.

A defect is flagged, never silently repaired. The pilot found a candidate whose
end date precedes its start date; a parser that quietly swapped them would have
turned a data error into a plausible-looking episode.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, timedelta

from packages.ids.keys import stable_id
from packages.temporal.dates import Censoring, Interval, PreciseDate

__all__ = ["Episode", "Defect", "merge_progressions",
           "merge_progressions_with_stats", "adult_window", "DEFECT_KINDS"]

DEFECT_KINDS = (
    "end_before_start",
    "no_start_date",
    "no_end_date_and_no_supported_activity",
    "partner_label_unresolved",
    "both_parties_adult_window_unknown",
)

#: Two statements join into one episode when the gap between them is at most
#: this. Wikidata usually abuts them exactly; a day of slack absorbs the
#: off-by-one between a closed end and an open start.
JOIN_SLACK_DAYS = 1


@dataclass(frozen=True)
class Defect:
    kind: str
    detail: str


@dataclass
class Episode:
    episode_id: str
    pair_key: str
    subject_qid: str
    partner_qid: str
    partner_label: str
    stages: list[str]
    start: PreciseDate | None
    end: PreciseDate | None
    has_reference: bool
    defects: list[Defect] = field(default_factory=list)
    review_status: str = "pending"
    merged_from: tuple[str, ...] = ()

    @property
    def scorable(self) -> bool:
        return not self.defects and self.start is not None

    def interval(self, last_supported_active: PreciseDate | None) -> Interval | None:
        if self.start is None:
            return None
        if self.end is not None:
            return Interval(self.start, self.end, Censoring.CLOSED)
        if last_supported_active is None:
            return None
        return Interval(self.start, None, Censoring.ONGOING, last_supported_active)

    def as_dict(self) -> dict:
        fmt = lambda d: None if d is None else {"value": d.value, "precision": d.precision.value}
        return {
            "episode_id": self.episode_id, "pair_key": self.pair_key,
            "subject_qid": self.subject_qid, "partner_qid": self.partner_qid,
            "partner_label": self.partner_label, "stages": self.stages,
            "start": fmt(self.start), "end": fmt(self.end),
            "has_reference": self.has_reference,
            "defects": [{"kind": d.kind, "detail": d.detail} for d in self.defects],
            "scorable": self.scorable, "review_status": self.review_status,
            "merged_from": list(self.merged_from),
        }


def _detect(cands: list, partner_label: str) -> list[Defect]:
    out: list[Defect] = []
    for c in cands:
        if c.start and c.end and c.end.latest() < c.start.earliest():
            out.append(Defect(
                "end_before_start",
                f"{c.relation} ends {c.end.value} before it starts {c.start.value}; "
                "flagged rather than swapped, because a swap turns a source error "
                "into a plausible episode",
            ))
    if not any(c.start for c in cands):
        out.append(Defect("no_start_date", "no candidate carries a start date"))
    if partner_label.startswith("Q") and partner_label[1:].isdigit():
        out.append(Defect(
            "partner_label_unresolved",
            f"the label service returned the bare id {partner_label}; the partner "
            "cannot be reviewed under a name",
        ))
    return out


def _dedupe_mirrored(group: list) -> tuple[list, int]:
    """Collapse one Wikidata statement read off BOTH people's items.

    When both halves of a couple are in the cohort, the fetcher reads the same
    spouse or unmarried_partner statement twice, once per item, and produces
    two candidates that agree on everything. They are not two relationships and
    not two stages of one: they are one fact, counted twice.

    Left alone they became two episodes, because the run-joining below sees two
    spans covering the same dates rather than two abutting ones. Ben Affleck
    and Ana de Armas produced two rows with the same dates and therefore the
    SAME stable_id, so anything keyed by episode_id silently lost one.

    Only an EXACT match collapses -- same relation, same start, same end, with
    precision. Two statements that differ anywhere are two candidates, and the
    defect detector downstream decides what that means. Guessing which of two
    disagreeing dates is right is not this function's job.

    A reference on either copy survives, because "Wikidata cites a source for
    this" is a property of the statement rather than of which item it was read
    from.
    """
    seen: dict[tuple, object] = {}
    refs: set[tuple] = set()
    collapsed = 0
    # Sorted so the surviving copy is the same on every run, whatever order the
    # cohort was iterated in.
    for c in sorted(group, key=lambda c: (
            c.relation,
            c.start.value if c.start else "",
            c.end.value if c.end else "",
            c.subject_qid)):
        key = (c.relation,
               (c.start.value, c.start.precision) if c.start else None,
               (c.end.value, c.end.precision) if c.end else None)
        if c.has_reference:
            refs.add(key)
        if key in seen:
            collapsed += 1
            continue
        seen[key] = c
    kept = []
    for key, c in seen.items():
        if key in refs and not c.has_reference:
            c = replace(c, has_reference=True)
        kept.append(c)
    return kept, collapsed


def merge_progressions(candidates: list) -> list[Episode]:
    """Group candidates by unordered pair and join abutting stages."""
    return merge_progressions_with_stats(candidates)[0]


def merge_progressions_with_stats(candidates: list) -> tuple[list[Episode], int]:
    """As ``merge_progressions``, plus how many mirrored duplicates collapsed.

    The count is returned rather than logged, because a silent collapse is how
    this bug hid in the first place.
    """
    by_pair: dict[str, list] = {}
    for c in candidates:
        by_pair.setdefault(c.pair_key, []).append(c)

    episodes: list[Episode] = []
    collapsed_total = 0
    for pk, group in sorted(by_pair.items()):
        group, collapsed = _dedupe_mirrored(group)
        collapsed_total += collapsed
        group = sorted(group, key=lambda c: (c.start.earliest() if c.start else date.max))
        runs: list[list] = []
        for c in group:
            if not runs:
                runs.append([c])
                continue
            prev = runs[-1][-1]
            joins = (
                prev.end is not None and c.start is not None
                and abs((c.start.earliest() - prev.end.latest()).days) <= JOIN_SLACK_DAYS
            )
            if joins:
                runs[-1].append(c)
            else:
                runs.append([c])

        for run in runs:
            first, last = run[0], run[-1]
            label = first.partner_label
            ep = Episode(
                episode_id=stable_id("ep", pk, first.relation,
                                     first.start.value if first.start else "nostart"),
                pair_key=pk,
                subject_qid=first.subject_qid,
                partner_qid=first.partner_qid,
                partner_label=label,
                stages=[c.relation for c in run],
                start=first.start,
                end=last.end,
                has_reference=any(c.has_reference for c in run),
                defects=_detect(run, label),
                merged_from=tuple(c.episode_id for c in run),
            )
            episodes.append(ep)
    return episodes, collapsed_total


def adult_window(
    interval: Interval,
    subject_dob: PreciseDate | None,
    partner_dob: PreciseDate | None,
) -> tuple[Interval | None, str | None]:
    """Clip an episode to the part where BOTH people were verifiably 18.

    An unknown birth date is not treated as "probably adult". Without both
    dates the episode is excluded, and the reason is returned.
    """
    if subject_dob is None or partner_dob is None:
        return None, "both_parties_adult_window_unknown"
    # latest() is the conservative reading: the person is 18 no earlier than
    # eighteen years after the LAST day their birth date could denote.
    thresholds = [
        _plus_18(subject_dob.latest()),
        _plus_18(partner_dob.latest()),
    ]
    clipped = interval.clip(not_before=max(thresholds))
    if clipped is None:
        return None, "outside_adult_window"
    return clipped, None


def _plus_18(d: date) -> date:
    try:
        return d.replace(year=d.year + 18)
    except ValueError:                      # 29 February
        return d.replace(year=d.year + 18, day=28) + timedelta(days=1)
