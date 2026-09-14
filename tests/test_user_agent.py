"""One User-Agent, defined once.

Wikipedia's User-Agent policy asks every client to identify itself, and a
project that does not is rate-limited or blocked. The string was copied into
six modules, and by the time anyone counted it had already drifted: five said
`celeb-couple-M0` and `modules/records/romance.py` said `M1`, announcing a
milestone this project has not reached and whose plan says to stop before.

The constant that is wrong is always the copy nobody reads, so the test is on
the count of definitions rather than on their contents.
"""
from __future__ import annotations

import re
from pathlib import Path

from packages.wiki.fetch import USER_AGENT

REPO = Path(__file__).resolve().parent.parent
HOME = REPO / "packages/wiki/fetch.py"


def _sources():
    for base in ("scripts", "modules", "packages"):
        yield from sorted((REPO / base).rglob("*.py"))


def test_only_one_file_defines_the_user_agent():
    definers = [p.relative_to(REPO) for p in _sources()
                if re.search(r"^USER_AGENT\s*=", p.read_text(), re.M)]
    assert definers == [HOME.relative_to(REPO)], (
        "the User-Agent is defined in more than one place, which is how "
        f"romance.py came to announce M1 while everything else said M0: {definers}"
    )


def test_the_user_agent_identifies_the_project_and_a_contact():
    """Wikimedia asks for a name and a way to reach whoever is running it."""
    assert "celeb-couple" in USER_AGENT
    assert "github.com/tonygwu/celeb-couple" in USER_AGENT


def test_the_user_agent_does_not_claim_a_milestone_the_plan_stops_before():
    """The plan's stop condition is "Stop after M0". romance.py said M1."""
    assert "M1" not in USER_AGENT
    assert re.search(r"celeb-couple-M0/", USER_AGENT), USER_AGENT


def test_every_wikimedia_request_carries_it():
    """A request built by hand somewhere else would bypass the shared header."""
    offenders = []
    for p in _sources():
        if p == HOME:
            continue
        text = p.read_text()
        for m in re.finditer(r"urllib\.request\.Request\(", text):
            line = text[: m.start()].count("\n") + 1
            window = text[m.start(): m.start() + 400]
            if "USER_AGENT" not in window:
                offenders.append(f"{p.relative_to(REPO)}:{line}")
    assert offenders == [], (
        "these build an HTTP request without the shared User-Agent: " +
        ", ".join(offenders))
