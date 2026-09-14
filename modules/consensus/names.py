"""When a plain-text table cell may be read as a person's name.

Both parsers in this package face the same question. Wikipedia's tables name
some people with a wiki-link and some in bare text -- Maxim's 2006 winner,
People's 2020 third entry, FHM's 2012 rank 4 -- and a bare cell is just as
often a note, a placeholder or a footnote fragment.

The rule lives here rather than in each parser because it was written twice
within an hour of consolidating the User-Agent for exactly this reason, and a
predicate duplicated across two files is one that will be tightened in one of
them.
"""

from __future__ import annotations

import re

__all__ = ["looks_like_a_name", "NAME_PATTERN"]

#: Two to five capitalised words, allowing the punctuation real names carry:
#: "Eva Longoria", "Rani Hudson Fujikawa", "Catherine Zeta-Jones", "J. Lo",
#: "Sinead O'Connor" and its typographic apostrophe.
#:
#: Deliberately strict, and the strictness is the point. A refused cell is
#: COUNTED and stays visible; an accepted one puts a person into the corpus.
#: A single capitalised word is refused because "Unknown", "None" and "Vacant"
#: are all commoner in these tables than a one-word stage name.
NAME_PATTERN = re.compile(
    r"^[A-Z][A-Za-z.'’\-]*(?: [A-Z][A-Za-z.'’\-]*){1,4}$")


def looks_like_a_name(text: str) -> bool:
    """True when ``text`` may be read as a person's name.

    Answering True does not put anyone in the corpus on its own: both callers
    then look the name up in ``name_to_person`` and emit an observation only
    for someone the roster already names.
    """
    return bool(NAME_PATTERN.match(text.strip()))
