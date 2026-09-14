"""One User-Agent, one article fetcher, for every Wikipedia and Wikidata call.

Wikipedia's User-Agent policy asks every client to identify itself and a
project that does not is rate-limited or blocked. The string was copied into
six modules, and by the time anyone counted it had already drifted: five said
``celeb-couple-M0`` and ``modules/records/romance.py`` said ``M1``, announcing
a milestone this project has not reached and whose plan says to stop before.

That is the whole argument for this module. A constant duplicated six times is
a constant that is wrong somewhere, and the copy that is wrong is the one
nobody reads.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request

__all__ = ["USER_AGENT", "WIKIPEDIA_API", "WIKIDATA_API", "request",
           "article_text"]

#: Identifies this client to Wikimedia. Change it here and nowhere else.
USER_AGENT = (
    "celeb-couple-M0/0.1 (https://github.com/tonygwu/celeb-couple; read-only research)"
)
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"


def request(api: str, params: dict, timeout: int = 60) -> dict:
    """GET a MediaWiki API endpoint and return the parsed JSON."""
    url = api + "?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        return json.load(fh)


def article_text(title: str, cache: dict[str, str] | None = None,
                 timeout: int = 60, pause: float = 0.2) -> str:
    """The plain-text extract of an English Wikipedia article.

    ``cache`` is optional and caller-owned: two verifiers read the same
    person's article for different reasons, and a caller checking 31
    relationships across 22 people should not fetch each article twice.

    A redirect is followed, because a roster name and an article title differ
    often enough to matter -- eleven of the hundred roster members have no
    English Wikidata label and are reached by their sitelink.

    An article that does not exist returns the empty string rather than
    raising. The callers report "not mentioned", which is what an empty
    article truthfully supports.
    """
    if cache is not None and title in cache:
        return cache[title]
    data = request(WIKIPEDIA_API, {
        "action": "query", "prop": "extracts", "explaintext": "1",
        "redirects": "1", "titles": title}, timeout=timeout)
    pages = data.get("query", {}).get("pages") or {}
    text = next(iter(pages.values()), {}).get("extract") or ""
    if cache is not None:
        cache[title] = text
        time.sleep(pause)
    return text
