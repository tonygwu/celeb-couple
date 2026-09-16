"""Merge pairing graphs without counting one romance twice.

The IMDb graph names a film by its tconst; the Wikidata graph names the same
film by its QID. So the two carry DIFFERENT `pairing_id`s for the same event,
and deduping on that id missed every overlap. Adam Sandler's row showed Just Go
with It, Murder Mystery and Murder Mystery 2 twice each, his romance count read
7 against a true 4, and cumulative double-counted every one of them.

Identity is therefore semantic: the unordered couple, the domain, the period,
and the normalised work title.
"""
from __future__ import annotations

import re
import unicodedata

__all__ = ["merge_graphs", "pairing_identity", "normalise_work"]

_PUNCT = re.compile(r"[^a-z0-9]+")

#: IMDb gives an alternate cut its own tconst, its own title and often its own
#: year. "Daredevil" (2003) and "Daredevil: The Director's Cut" (2004) are one
#: film, and counting both gave Ben Affleck two romances with Jennifer Garner.
#: There is no field in the bulk dumps linking a cut to its original, so the
#: suffix is stripped instead.
_EDITION = re.compile(
    r"\b(the )?(directors?|extended|unrated|special|theatrical|ultimate|final|"
    r"collectors?|anniversary|remastered|uncut|redux)\b.*$")


def normalise_work(title: str | None) -> str:
    """Two sources punctuate differently. 'Mr. & Mrs. Smith' and 'Mr & Mrs
    Smith' are one film; 'Murder Mystery' and 'Murder Mystery 2' are two."""
    if not title:
        return ""
    flat = unicodedata.normalize("NFKD", str(title)).encode("ascii", "ignore").decode()
    flat = _PUNCT.sub(" ", flat.casefold()).strip()
    base = _EDITION.sub("", flat).strip()
    # Never strip the whole title: a film actually called "The Final Cut" must
    # keep its name rather than collapse into every other stripped title.
    return base or flat


def pairing_identity(p: dict) -> tuple | None:
    """What makes two records the SAME romance, or None if it cannot be told.

    The couple is unordered, because a graph that put the woman in `male_qid`
    would otherwise read as a different romance. Domain is part of the key: a
    couple who co-starred AND dated is two separate facts about them.
    """
    m, f = p.get("male_qid"), p.get("female_qid")
    if not m or not f:
        return None
    couple = tuple(sorted((m, f)))
    work = normalise_work(p.get("work"))
    if p.get("domain") == "on_screen" and work:
        # The YEAR IS DELIBERATELY NOT IN THIS KEY. Two sources disagree about
        # a film's year -- release against production, or an alternate cut
        # dated a year later -- and one couple in one film is one romance
        # whichever year is recorded. A re-teaming is a different title and
        # stays separate.
        return ("on_screen", couple, work)
    # Real life keeps the period: Ben Affleck and Jennifer Lopez were together
    # in 2004 and again in 2022, and those are two relationships, not one.
    return (p.get("domain"), couple, str(p.get("period") or ""), work)


def merge_graphs(sources: list[tuple[str, list[dict]]]) -> tuple[list[dict], dict]:
    """Merge in order. The FIRST source to carry a romance keeps it.

    Order matters and is the caller's choice: the IMDb records carry weight,
    confidence and character names that the Wikidata ones do not, so IMDb is
    passed first.

    A pairing whose identity cannot be determined is KEPT, never merged into
    another, and counted. Silently collapsing two unidentifiable records would
    delete a real romance to tidy up a missing field.
    """
    kept: list[dict] = []
    seen: dict[tuple, str] = {}
    stats = {"seen": 0, "duplicates_dropped": 0, "without_both_qids": 0,
             "by_source": {}, "dropped_examples": []}
    for name, rows in sources:
        stats["by_source"].setdefault(name, 0)
        for p in rows:
            stats["seen"] += 1
            ident = pairing_identity(p)
            if ident is None:
                stats["without_both_qids"] += 1
                kept.append(p)
                stats["by_source"][name] += 1
                continue
            if ident in seen:
                stats["duplicates_dropped"] += 1
                if len(stats["dropped_examples"]) < 10:
                    stats["dropped_examples"].append(
                        {"kept_from": seen[ident], "dropped_from": name,
                         "work": p.get("work"), "period": p.get("period"),
                         "who": f"{p.get('male')} + {p.get('female')}"})
                continue
            seen[ident] = name
            kept.append(p)
            stats["by_source"][name] += 1
    return kept, stats
