"""Relationship and birth-date ingestion from Wikidata.

Wikidata is CC0 and carries date qualifiers with an explicit precision code, so
it is the one route in this project where facts can be retained and republished
with no attribution obligation.

It is also INCOMPLETE, measured 2026-09-13: a probe of four subjects returned
13 episodes and missed a widely reported earlier engagement for one of them and
an eight-year relationship for another. So these records are CANDIDATES. Every
one enters review before it can affect a published number.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace

from packages.ids.keys import pair_key, stable_id
from packages.temporal.dates import Censoring, Interval, PreciseDate, from_wikidata

__all__ = ["RelationshipCandidate", "fetch_relationships", "fetch_birth_dates",
           "fetch_gender", "fetch_labels", "query_with_retry", "SPARQL",
           "TRANSIENT_HTTP_STATUS", "WikidataQueryTimeout", "TruncatedResult",
           "batched_query", "LOOKUP_FAILURES", "LABEL_SOURCES"]

SPARQL = "https://query.wikidata.org/sparql"
#: Imported, not copied. See packages/wiki/fetch.py.
from packages.wiki.fetch import USER_AGENT  # noqa: E402,F401
#: Wikidata asks for polite pacing and will 429. Commons returned 429 after
#: about twenty sequential calls during the feasibility probe.
PACE_SECONDS = 1.2


#: Batches whose lookup failed outright, so "still a bare Q-id" can be told
#: apart from "this entity has no English label". Module-level rather than a
#: return value because the single caller wants the labels, and an ambiguity
#: nobody can see is worse than a global nobody reads.
LOOKUP_FAILURES: list[dict] = []
#: qid -> "label" | "enwiki_sitelink", how each name was actually obtained.
LABEL_SOURCES: dict[str, str] = {}


def fetch_labels(qids: list[str], timeout: int = 45) -> dict[str, str]:
    """English labels via wbgetentities, as a fallback for the label SERVICE.

    Measured 2026-09-14, and the cause was not what it looked like. Two pilot
    partners and ten roster partners came back as bare Q-ids, so their episodes
    were flagged partner_label_unresolved and excluded as defective. It was not a
    SERVICE quirk: Q13909 and Q2023710 have NO English label in Wikidata at all,
    though they carry labels in dozens of other languages.

    They do have English Wikipedia sitelinks, which name them Angelina Jolie and
    Tom Holland. A sitelink title is a sourced name rather than a guess, so it is
    the fallback. A person with neither stays unresolved and their episode stays
    excluded, which is the correct outcome for a partner nobody can name.
    """
    import urllib.error

    out: dict[str, str] = {}
    for i in range(0, len(qids), 50):          # the API caps ids per call
        chunk = qids[i:i + 50]
        url = ("https://www.wikidata.org/w/api.php?"
               + urllib.parse.urlencode({
                   "action": "wbgetentities", "ids": "|".join(chunk),
                   "props": "labels|sitelinks", "sitefilter": "enwiki",
                   "languages": "en", "format": "json"}))
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as fh:
                blob = json.load(fh)
        except (urllib.error.URLError, TimeoutError) as exc:
            # A failed batch and a batch whose entities genuinely have no
            # English label both end as "still a bare Q-id", and the caller
            # could not tell them apart. That ambiguity already cost an
            # investigation: Q13909 was first diagnosed as a SERVICE failure
            # and turned out to have no English label at all.
            LOOKUP_FAILURES.append({"qids": list(chunk), "error": f"{type(exc).__name__}: {exc}"})
            continue
        for qid, entity in (blob.get("entities") or {}).items():
            label = ((entity.get("labels") or {}).get("en") or {}).get("value")
            source = "label"
            if not label:
                # no English label; the English Wikipedia article title is a
                # sourced name for the same entity
                label = ((entity.get("sitelinks") or {}).get("enwiki") or {}).get("title")
                source = "enwiki_sitelink"
            if label:
                out[qid] = label
                # A name from an article title is different provenance from a
                # name from a label. In a project whose product is
                # traceability, which route supplied a person's name is worth
                # being able to answer.
                LABEL_SOURCES[qid] = source
        time.sleep(PACE_SECONDS)
    return out


class WikidataQueryTimeout(RuntimeError):
    """The query service gave up part-way and said so INSIDE a 200 response.

    Measured 2026-09-15 and worth stating plainly, because it is the exact
    shape of failure that looks like success. The Wikidata Query Service caps
    a query at about sixty seconds. It does not answer with a 503. It streams
    result rows, and when the cap hits it stops mid-JSON and appends its own
    log to the same body:

        "valSPARQL-QUERY: queryStr=
        SELECT DISTINCT ?seed ...
        java.util.concurrent.TimeoutException

    The status line stays 200 and the body is 595 KB, so every liveness check
    passes. What arrives is a truncated result set with a Java stack trace
    glued to the end of it.

    `json.loads` happens to reject this, which is the only reason it was ever
    noticed. That is luck, not a guard. This exception makes the diagnosis
    explicit so the caller can do the one thing that actually helps, which is
    ask for less in one query.
    """


#: The strings the service leaves in a timed-out body. Two of them, because a
#: check on the Java class name alone would miss a differently worded abort,
#: and one on the query echo alone would fire on a query about SPARQL itself.
_TIMEOUT_MARKERS = ("java.util.concurrent.TimeoutException",
                    "QueryTimeoutException",
                    "SPARQL-QUERY: queryStr=")


def _query(sparql: str, timeout: int = 60) -> list[dict]:
    url = SPARQL + "?" + urllib.parse.urlencode({"query": sparql})
    req = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        body = fh.read().decode("utf-8", errors="replace")
    try:
        return json.loads(body)["results"]["bindings"]
    except json.JSONDecodeError:
        # Order matters. The markers are only consulted once the body has
        # already failed to parse, so a legitimate result that happens to
        # quote one of them is never mistaken for a timeout. A body that is
        # unparseable for any OTHER reason re-raises unchanged rather than
        # being relabelled into a diagnosis nobody verified.
        if any(marker in body for marker in _TIMEOUT_MARKERS):
            raise WikidataQueryTimeout(
                f"the query service aborted after {len(body)} bytes of a 200 "
                "response and appended its own timeout log. The query asks for "
                "too much at once; split it.") from None
        raise


class TruncatedResult(RuntimeError):
    """A batch came back at its LIMIT, so rows were dropped with nothing said.

    Measured 2026-09-15. `fetch_onscreen_candidates.py` ran ONE query with
    `LIMIT 400` against a 100-name roster that produces 2570 rows. Wikidata
    returned the first 400 and dropped 2170 in silence, and the artifact
    recorded 136 co-starring pairs across 74 films as if that were the answer.
    The real figure is 808 pairs across 502 films, and 25 of the 100 roster
    members had NO pair at all, so Gigli, Armageddon and Ghosted each looked
    like a gap in Wikidata rather than a gap in the query.

    A short result set nobody can see is worse than a crash. This raises.
    """


def batched_query(build, items: list, chunk_size: int, limit: int,
                  label: str = "batch", timeout: int = 180,
                  on_unreachable=None, log=print) -> list[dict]:
    """Run one query per chunk of `items`, guarding both silent-loss modes.

    `build(chunk)` returns the SPARQL for that chunk. Two different failures
    are refused rather than absorbed, and they are not the same failure:

    AT THE LIMIT. The service answered fully and the answer was capped, so
    rows were dropped. Nothing can rescue that from here, and it raises.

    TIMED OUT. The service answered 200, streamed part of the result and glued
    a Java stack trace to the end of the body. Retrying the same query is
    pointless because the query is what is too big, so the chunk is HALVED and
    each half tried again, down to a single item. An item that still times out
    alone is handed to `on_unreachable` and is never quietly skipped; with no
    handler the timeout propagates.
    """
    rows: list[dict] = []
    queue = [list(items[i:i + chunk_size])
             for i in range(0, len(items), chunk_size)]
    done = 0
    while queue:
        chunk = queue.pop(0)
        try:
            got = query_with_retry(build(chunk), timeout=timeout)
        except WikidataQueryTimeout as exc:
            if len(chunk) == 1:
                if on_unreachable is None:
                    raise
                log(f"    {label}: {chunk[0]} times out on its own; "
                    "recorded as unreachable")
                on_unreachable(chunk[0], exc)
                continue
            half = len(chunk) // 2
            log(f"    {label}: chunk of {len(chunk)} timed out, splitting into "
                f"{half} + {len(chunk) - half}")
            queue[:0] = [chunk[:half], chunk[half:]]
            time.sleep(PACE_SECONDS)
            continue
        if len(got) >= limit:
            raise TruncatedResult(
                f"{label} chunk of {len(chunk)} returned {len(got)} rows, at or "
                f"over its LIMIT of {limit}. Wikidata dropped the rest silently. "
                "Use a smaller chunk size or a larger limit.")
        done += 1
        log(f"    {label} {done}: {len(chunk)} item(s) -> {len(got)} rows")
        rows += got
        time.sleep(PACE_SECONDS)
    return rows


#: Statuses the Wikidata Query Service returns when it is momentarily
#: unavailable rather than when the query is wrong. Measured 2026-09-15: a
#: batched co-star query got a plain 502 on its third batch, which crashed the
#: whole fetch after two batches of good work. A 400 is a bad query and must
#: never be retried, because retrying it hides the error behind a delay.
TRANSIENT_HTTP_STATUS = frozenset({429, 500, 502, 503, 504})

#: Retries are COUNTED, not swallowed. The caller reads this and records it in
#: the artifact, so a run that only succeeded on the fourth attempt does not
#: look identical to one that succeeded first time.
RETRIES: list[dict] = []


def query_with_retry(sparql: str, timeout: int = 60, attempts: int = 4,
                     backoff: float = 3.0) -> list[dict]:
    """`_query` with bounded retries on a transient endpoint failure.

    This is NOT a permissive wrapper. A 400 (bad query) raises on the first
    attempt, and running out of attempts raises the last error rather than
    returning a short list, because a silently short result set is exactly the
    defect this module was fixed for.
    """
    import urllib.error

    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return _query(sparql, timeout=timeout)
        except urllib.error.HTTPError as exc:
            if exc.code not in TRANSIENT_HTTP_STATUS:
                raise
            last = exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last = exc
        RETRIES.append({"attempt": attempt, "error": f"{type(last).__name__}: {last}"})
        # Printed as well as recorded. A silent retry makes a run that is
        # backing off look identical to a run that has hung, which is the
        # confusion AGENTS.md's "arm a watcher" note is about.
        print(f"    wikidata retry {attempt}/{attempts}: {type(last).__name__}: {last}",
              flush=True)
        if attempt < attempts:
            time.sleep(backoff * attempt)
    raise last


def _val(row: dict, key: str) -> str | None:
    return row.get(key, {}).get("value")


@dataclass(frozen=True)
class RelationshipCandidate:
    episode_id: str
    pair_key: str
    subject_qid: str
    partner_qid: str
    partner_label: str
    relation: str                      # "spouse" | "unmarried_partner"
    start: PreciseDate | None
    end: PreciseDate | None
    has_reference: bool
    review_status: str = "pending"

    def interval(self, as_of: PreciseDate) -> Interval | None:
        if self.start is None:
            return None
        if self.end is not None:
            return Interval(self.start, self.end, Censoring.CLOSED)
        # No supported end date. An ongoing episode closes at the last supported
        # active date -- never at the run date and never at today.
        return Interval(self.start, None, Censoring.ONGOING, last_supported_active=as_of)

    def as_dict(self) -> dict:
        return {
            "episode_id": self.episode_id, "pair_key": self.pair_key,
            "subject_qid": self.subject_qid, "partner_qid": self.partner_qid,
            "partner_label": self.partner_label, "relation": self.relation,
            "start": None if not self.start else
                {"value": self.start.value, "precision": self.start.precision.value},
            "end": None if not self.end else
                {"value": self.end.value, "precision": self.end.precision.value},
            "has_reference": self.has_reference,
            "review_status": self.review_status,
        }


_REL_QUERY = """
SELECT ?p ?rel ?partner ?partnerLabel ?start ?sPrec ?end ?ePrec ?ref WHERE {
  VALUES ?p { %s }
  { ?p p:P26 ?st . ?st ps:P26 ?partner . BIND("spouse" AS ?rel) }
  UNION
  { ?p p:P451 ?st . ?st ps:P451 ?partner . BIND("unmarried_partner" AS ?rel) }
  OPTIONAL { ?st pq:P580 ?start . ?st pqv:P580 [ wikibase:timePrecision ?sPrec ] }
  OPTIONAL { ?st pq:P582 ?end   . ?st pqv:P582 [ wikibase:timePrecision ?ePrec ] }
  OPTIONAL { ?st prov:wasDerivedFrom ?ref }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def fetch_relationships(qids: list[str]) -> list[RelationshipCandidate]:
    """One batched query, so the endpoint is hit once rather than per person."""
    values = " ".join(f"wd:{q}" for q in qids)
    rows = _query(_REL_QUERY % values)
    time.sleep(PACE_SECONDS)

    seen: dict[tuple, RelationshipCandidate] = {}
    for row in rows:
        subject = (_val(row, "p") or "").rsplit("/", 1)[-1]
        partner = (_val(row, "partner") or "").rsplit("/", 1)[-1]
        relation = _val(row, "rel") or ""
        if not subject or not partner:
            continue
        src = f"wikidata:{subject}:{relation}:{partner}"
        start = end = None
        if _val(row, "start") and _val(row, "sPrec"):
            try:
                start = from_wikidata(_val(row, "start"), int(_val(row, "sPrec")), src)
            except ValueError:
                start = None   # coarser than a year: refused, not widened
        if _val(row, "end") and _val(row, "ePrec"):
            try:
                end = from_wikidata(_val(row, "end"), int(_val(row, "ePrec")), src)
            except ValueError:
                end = None
        key = (subject, partner, relation)
        cand = RelationshipCandidate(
            episode_id=stable_id("rle", subject, partner, relation),
            pair_key=pair_key(subject, partner),
            subject_qid=subject, partner_qid=partner,
            partner_label=_val(row, "partnerLabel") or partner,
            relation=relation, start=start, end=end,
            has_reference=bool(_val(row, "ref")),
        )
        # several reference rows collapse to one candidate; keep the richest
        prior = seen.get(key)
        if prior is None or (cand.start and not prior.start) or (cand.end and not prior.end):
            seen[key] = cand
        elif cand.has_reference and not prior.has_reference:
            seen[key] = cand
    # The label SERVICE sometimes returns a bare Q-id. Look those up directly
    # rather than excluding a real record over one endpoint's quirk.
    unlabelled = sorted({c.partner_qid for c in seen.values()
                         if c.partner_label == c.partner_qid})
    if unlabelled:
        labels = fetch_labels(unlabelled)
        if labels:
            seen = {k: (c if c.partner_qid not in labels
                        else replace(c, partner_label=labels[c.partner_qid]))
                    for k, c in seen.items()}
    return sorted(seen.values(), key=lambda c: (c.subject_qid, c.partner_label))


_GENDER_QUERY = """
SELECT ?p ?genderLabel WHERE {
  VALUES ?p { %s }
  ?p wdt:P21 ?gender .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def fetch_gender(qids: list[str]) -> dict[str, str]:
    """Sourced public-identity gender from Wikidata P21.

    The plan is explicit that this is a SOURCED field. It is never inferred from
    appearance and never from who somebody dated, and a person Wikidata does not
    record is left out of the map rather than guessed at, because an absent
    value is unknown and not a default.
    """
    rows = _query(_GENDER_QUERY % " ".join(f"wd:{q}" for q in qids))
    time.sleep(PACE_SECONDS)
    out: dict[str, str] = {}
    for row in rows:
        qid = (_val(row, "p") or "").rsplit("/", 1)[-1]
        label = (_val(row, "genderLabel") or "").strip().lower()
        if qid and label and not label.startswith("q"):
            out[qid] = label
    return out


_BIRTH_QUERY = """
SELECT ?p ?dob ?prec WHERE {
  VALUES ?p { %s }
  ?p p:P569 ?st . ?st ps:P569 ?dob .
  ?st psv:P569 [ wikibase:timePrecision ?prec ] .
}
"""


def fetch_birth_dates(qids: list[str]) -> dict[str, PreciseDate]:
    """Birth dates with precision, for the adult-window clip."""
    rows = _query(_BIRTH_QUERY % " ".join(f"wd:{q}" for q in qids))
    time.sleep(PACE_SECONDS)
    out: dict[str, PreciseDate] = {}
    for row in rows:
        qid = (_val(row, "p") or "").rsplit("/", 1)[-1]
        try:
            out[qid] = from_wikidata(
                _val(row, "dob"), int(_val(row, "prec")), f"wikidata:{qid}:P569"
            )
        except (ValueError, TypeError):
            continue
    return out
