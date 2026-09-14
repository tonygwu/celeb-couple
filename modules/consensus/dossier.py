"""Build the text a judge sees for one (person, period).

WHAT A DOSSIER DELIBERATELY DOES NOT CONTAIN
--------------------------------------------
No photograph.  No partner identity.  No other person's dossier.  No roster,
no ranking, no indication of who else is being scored.  That isolation is what
makes "score people independently of their partners" a property of the system
rather than an instruction someone has to follow.

Syndicated copies are collapsed to their original source BEFORE rendering, so
five sites reprinting one magazine's list arrive as one observation and copy
volume cannot act as corroboration.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

from packages.ids.keys import json_sha256, stable_id
from packages.schema.records import EvidenceType, ListEdition, Observation

__all__ = ["Dossier", "build_dossier", "collapse_syndication", "redact_name",
           "residual_identity_tokens"]

#: Name tokens shorter than this are not redacted on their own.  Redacting a
#: two-letter token would hit ordinary words; verbatim-index learned this the
#: expensive way when matching a surname also replaced the contraction "that\'s"
#: 34 times in one transcript.  The full name is always redacted regardless.
MIN_TOKEN_LEN = 4


def redact_name(text: str, display_name: str, aliases: tuple[str, ...] = ()) -> str:
    """Replace the subject\'s name wherever it appears, including inside excerpts.

    Anonymising only the Subject line is not anonymising: a ranked-list excerpt
    reads "12. Ada Vance" and hands the judge the identity anyway.
    """
    candidates = [display_name, *aliases]
    for alias in (display_name, *aliases):
        candidates.extend(t for t in alias.split() if len(t) >= MIN_TOKEN_LEN)
    # longest first, so "Ada Vance" is replaced before "Vance"
    for token in sorted(set(candidates), key=len, reverse=True):
        text = re.sub(rf"\b{re.escape(token)}\b", "[SUBJECT]", text, flags=re.IGNORECASE)
    return text


def residual_identity_tokens(
    text: str, display_name: str, aliases: tuple[str, ...] = ()
) -> tuple[str, ...]:
    """Name tokens still visible in ``text`` after redaction.

    ``redact_name`` skips tokens shorter than ``MIN_TOKEN_LEN`` on purpose:
    blanking "de" or "Ben" across ordinary prose would destroy it. The cost is
    that a short first name survives, and seven of the 37 names in this
    project's own cohort and partner universe have one -- Ben, Ana, Liv, Len.

    The identity-leakage probe cannot see that by itself. Run on a name whose
    tokens are all long it reports honestly; run on "Ben Affleck" it would
    report "no leakage" while the judge had read "Ben". A probe blind to its own
    blind spot reports clean either way, so this returns the blind spot instead.

    Returns the surviving tokens in the order they appear in the name, so a
    caller can report exactly what redaction could not remove.
    """
    seen: list[str] = []
    for alias in (display_name, *aliases):
        for token in alias.split():
            if len(token) >= MIN_TOKEN_LEN or not token.strip(".,'"):
                continue
            if token in seen:
                continue
            if re.search(rf"\b{re.escape(token)}\b", text, flags=re.IGNORECASE):
                seen.append(token)
    return tuple(seen)


def collapse_syndication(observations: list[Observation]) -> tuple[list[Observation], int]:
    """Keep one observation per (person, original source, evidence type, payload).

    Returns (kept, dropped_count).  Preference goes to the non-syndicated copy
    when one is present, so the canonical edition is the one that survives.
    """
    buckets: dict[str, list[Observation]] = {}
    for o in observations:
        key = json_sha256(
            [o.person_id, o.lineage.original_source, o.evidence_type.value, o.observed]
        )
        buckets.setdefault(key, []).append(o)
    kept: list[Observation] = []
    dropped = 0
    for group in buckets.values():
        group.sort(key=lambda o: (o.lineage.is_syndicated_copy, o.observation_id))
        kept.append(group[0])
        dropped += len(group) - 1
    kept.sort(key=lambda o: o.observation_id)
    return kept, dropped


@dataclass(frozen=True)
class Dossier:
    dossier_id: str
    person_id: str
    period: str
    text: str
    observation_ids: tuple[str, ...]
    distinct_original_sources: int
    distinct_publishers: int
    syndicated_copies_dropped: int
    anonymised: bool
    #: Name tokens redaction could not remove, because they are shorter than
    #: MIN_TOKEN_LEN. Empty unless ``anonymise`` was requested. A non-empty
    #: tuple means the identity-leakage probe was NOT fully blind for this
    #: dossier, and a clean result from it says less than it appears to.
    residual_name_tokens: tuple[str, ...] = ()

    @property
    def is_empty(self) -> bool:
        return not self.observation_ids


def _render_observation(o: Observation, edition: ListEdition, n: int) -> str:
    ob = o.observed
    head = f"[{o.observation_id}] "
    when = (
        f"published {o.published_at.value} ({o.published_at.precision.value}), "
        f"concerns {o.concerns_period.value} ({o.concerns_period.precision.value})"
    )
    if o.retrospective:
        when += " — RETROSPECTIVE: written later about this period"

    if o.evidence_type is EvidenceType.ORDERED_RANK:
        depth = ob.get("list_length")
        where = (f"Ranked {ob['rank']} of {depth}" if depth
                 else f"Ranked {ob['rank']}, but the source does not state how "
                      f"long the list was, so how selective this placement is "
                      f"cannot be judged from it")
        body = (
            f"{where} in \"{edition.title}\". "
            f"The page establishes the order as a ranking: {ob['order_basis']!r}."
        )
    elif o.evidence_type is EvidenceType.UNORDERED_INCLUSION:
        size = ob.get("list_length")
        how_many = (f"a set of {size} names" if size
                    else "a set whose size the source does not state")
        body = (
            f"Included in \"{edition.title}\", {how_many}. "
            "The source does not state an order, so no position is implied."
        )
    elif o.evidence_type is EvidenceType.EDITORIAL_AWARD:
        role = "winner" if ob.get("winner") else "named honoree"
        body = f"Named {role} of \"{ob['award_name']}\"."
    elif o.evidence_type is EvidenceType.PUBLICATION_RATING:
        body = (
            f"This publication gave its own rating of {ob['rating_value']} on its "
            f"own {ob['rating_scale']} scale. That is their number, not a score "
            "you are being asked to reproduce."
        )
    elif o.evidence_type is EvidenceType.BALLOT_PREFERENCE:
        body = (
            f"Took {ob['vote_share']:.0%} of a ballot described as: "
            f"{ob['ballot_description']}."
        )
        if ob.get("placement") is not None:
            body += f" Published placement: {ob['placement']}."
        else:
            body += " The published placement is not available, so the share alone is known."
    else:
        # The excerpt carries the substance, on the `quoted:` line below, but
        # saying so makes the judge's job explicit rather than implied.
        body = ("Dated commentary about the person's appearance. The quoted text "
                "below is the whole of the judgment.")

    return (
        f"{head}{body}\n"
        f"    publisher: {edition.publisher} | {when}\n"
        f"    pool the source drew from: {edition.candidate_set_described}\n"
        f"    quoted: {o.excerpt!r} (at {o.excerpt_locator})"
    )


def build_dossier(
    person_id: str,
    display_name: str,
    period: str,
    observations: list[Observation],
    editions: dict[str, ListEdition],
    *,
    anonymise: bool = False,
    shuffle_seed: int | None = None,
    aliases: tuple[str, ...] = (),
) -> Dossier:
    """Render one person-period into judge-facing text.

    ``anonymise`` replaces the name with a neutral label, for the
    identity-leakage evaluation: the same evidence under a different name must
    score the same.  ``shuffle_seed`` reorders the observations, for the
    order-sensitivity evaluation.
    """
    # Every scoring script passes `names.get(person, person)`, so a person
    # whose label never resolved arrives here as their own Wikidata id and the
    # judge is asked to rate "Subject: Q13909". Two partners really did enter
    # this corpus as bare Q-ids -- they carry no English label at all -- and an
    # estimate attributed to an identifier is not a cheaper estimate, it is a
    # different thing. Checked BEFORE anonymisation, which would replace the
    # id with [SUBJECT] and hide the problem rather than fix it.
    if re.fullmatch(r"Q\d+", display_name.strip()):
        raise ValueError(
            f"refusing to build a dossier for an unresolved name: "
            f"display_name is {display_name!r}, which is a Wikidata id rather "
            f"than a person. Resolve the label first (see fetch_labels, which "
            f"falls back to the English Wikipedia sitelink title) or leave the "
            f"person unscored."
        )

    kept, dropped = collapse_syndication(observations)
    if shuffle_seed is not None:
        random.Random(shuffle_seed).shuffle(kept)

    subject = "[SUBJECT]" if anonymise else display_name
    lines = [
        f"Subject: {subject}",
        f"Period under assessment: {period}",
        "",
        f"Dated published judgments found for this period ({len(kept)}):",
        "",
    ]
    if kept:
        for i, o in enumerate(kept, 1):
            lines.append(_render_observation(o, editions[o.list_edition_id], i))
            lines.append("")
    else:
        lines += [
            "(none)",
            "",
            "No dated published judgment about this person's appearance was found "
            "for this period. Return unscored.",
            "",
        ]

    text = "\n".join(lines).rstrip() + "\n"
    residual: tuple[str, ...] = ()
    if anonymise:
        # Redact AFTER rendering, so the name is caught in excerpts and titles
        # too, not only on the Subject line.
        text = redact_name(text, display_name, aliases)
        # And report what redaction could not remove, rather than letting a
        # leakage probe report "clean" while the judge read a short first name.
        residual = residual_identity_tokens(text, display_name, aliases)
    publishers = {editions[o.list_edition_id].publisher for o in kept}
    sources = {o.lineage.original_source for o in kept}
    return Dossier(
        dossier_id=stable_id("dos", person_id, period),
        person_id=person_id,
        period=period,
        text=text,
        observation_ids=tuple(o.observation_id for o in kept),
        distinct_original_sources=len(sources),
        distinct_publishers=len(publishers),
        syndicated_copies_dropped=dropped,
        residual_name_tokens=residual,
        anonymised=anonymise,
    )
