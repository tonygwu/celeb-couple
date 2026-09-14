"""Typed failure categories.  Every failure gets one; none gets a bare count.

Declared once, derived from, never re-typed at a call site.  An inline subset
in verbatim-index relabelled 9 load-shedding failures as crashes.
"""

from __future__ import annotations

__all__ = ["ALL_ERROR_TYPES", "classify_detail", "ErrorType"]

E_CLI_NONZERO = "cli_nonzero_exit"
E_TIMEOUT = "cli_timeout"
E_EMPTY = "empty_response"
E_NO_JSON = "no_json_in_response"
E_JSON_PARSE = "json_parse_error"
E_SCHEMA = "schema_validation_failed"
E_MODEL_MISMATCH = "model_identity_mismatch"
E_AUTH_QUOTA = "auth_or_quota"
E_TRANSIENT = "transient_retryable"
E_REFUSED = "judge_declined_to_score"
E_BUDGET = "budget_cap_reached"
E_ROUTE_RESTRICTED = "source_route_restricted"
E_CITES_NOTHING = "rationale_cites_no_observation"
E_TOOL_USE = "judge_attempted_tool_use"

ALL_ERROR_TYPES: tuple[str, ...] = (
    E_CLI_NONZERO, E_TIMEOUT, E_EMPTY, E_NO_JSON, E_JSON_PARSE, E_SCHEMA,
    E_MODEL_MISMATCH, E_AUTH_QUOTA, E_TRANSIENT, E_REFUSED, E_BUDGET,
    E_ROUTE_RESTRICTED, E_CITES_NOTHING, E_TOOL_USE, "unclassified_failure",
)

ErrorType = str


E_UNCLASSIFIED = "unclassified_failure"


def classify_detail(detail: str) -> ErrorType:
    """Recover a label from an error string by LONGEST prefix match.

    Longest wins so a shorter label cannot shadow a longer one that starts
    with the same characters.

    An unrecognised string becomes ``unclassified_failure``, NOT
    ``transient_retryable``. The old default meant an unknown permanent error
    was labelled retryable, so a caller would retry it three times, spend the
    quota, and file it in the taxonomy under a cause it does not have. "I do
    not recognise this" and "this will probably work next time" are different
    statements and only one of them is true by default.
    """
    best = ""
    for label in ALL_ERROR_TYPES:
        if detail.startswith(label) and len(label) > len(best):
            best = label
    return best or E_UNCLASSIFIED


#: Quota exhaustion and a transient auth race arrive looking alike: an OAuth
#: refresh race carries a 429.  Reading that as exhaustion benches a healthy
#: account.  These phrases are the ones that mean genuine exhaustion.
QUOTA_PHRASES = (
    "you've hit your",
    "you have hit your",
    "you've reached your",
    "usage limit",
    "spend limit",
    "session limit",
    "weekly limit",
)


def classify_cli_failure(returncode: int, stdout: str, stderr: str) -> ErrorType:
    """Tell a quota stop from a crash by reading what the CLI printed."""
    blob = f"{stdout}\n{stderr}".lower()
    if any(p in blob for p in QUOTA_PHRASES):
        return E_AUTH_QUOTA
    if "429" in blob or "rate limit" in blob or "overloaded" in blob:
        return E_TRANSIENT
    if returncode != 0:
        return E_CLI_NONZERO
    return E_EMPTY
