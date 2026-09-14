# Does coverage scale with roster size?

Generated from the artifacts by `scripts/scaling_report.py`. The pilot ran 14 people; the plan's full 100-name roster was put through the same free stages. Both rosters were chosen on prominence before any check of how easy anyone is to score.

## The answer

**Coverage does not scale with roster size. A 7-fold larger roster produced 3.2x the observations and 9.2x the episodes, and the number of COMPARABLE jointly covered pairings went from 1 to 1.**

Joint coverage is a conjunction of independently rare conditions: both people judged, near the same year, by the same kind of evidence. Each is uncommon, so the conjunction is rarer than any of them, and growing the roster multiplies the numerator and the denominator together.

## The numbers

| Metric | Pilot (14) | Roster (100) |
|---|---|---|
| Roster size | 14 | 100 |
| Relationship episodes (scorable) | 26 | 239 |
| Observations | 41 | 131 |
| People with any observation (incl. partners) | 14 | 61 |
| ...of those, on the roster itself | 10 | 49 |
| Person-periods | 39 | 127 |
| Mean observations per person-period | 1.051 | 1.031 |
| Person-periods with 2+ publishers | 2 | 4 |
| Episodes with evidence on BOTH sides anywhere | — | 20 |
| Jointly covered within ±1 year | 4 | 5 |
| ...of those, COMPARABLE (same evidence shape) | 1 | 1 |

## What a source would have to look like

"Find better sources" is not a specification, so `scripts/source_requirement.py` turns it into one: simulate a hypothetical annual ranked list over the REAL episode structure and the REAL roster, and count how many of the 239 scorable episodes come out jointly covered.

| Names per year | p10 | median | p90 |
|---|---|---|---|
| 1 | 0 | 0 | 0 |
| 5 | 0 | 1 | 4 |
| 10 | 2 | 4 | 7 |
| 25 | 8 | 13 | 18 |
| 50 | 20 | 23 | 25 |
| 100 | 25 | 25 | 25 |
| 200 | 25 | 25 | 25 |
| 400 | 25 | 25 | 25 |

Read against what actually exists:

| Source | Names per year |
|---|---|
| Sexiest Man Alive | 1 |
| People Most Beautiful cover | 1 |
| Maxim Hot 100, as published on Wikipedia | 1 |
| FHM top ten, as on Wikipedia | 10 |
| FHM full list, **not available on a permitted route** | 100 |

**One name a year covers nothing.** Every award source this project can currently reach sits on that rung. That is not a shortfall to be closed by adding more such sources.

**The requirement is about 100 names a year.** At that depth the median reaches 25 episodes. That is the shape of FHM's real published list, which exists and is not reachable: Wikipedia carries only its top ten, and the publisher blocks the AI crawlers.

**It saturates there.** Beyond 100 names a year the median stays at 25, because the binding constraint becomes the roster and the era span rather than the list depth. So the ceiling for this design, with a perfect source, is 25 of 239 episodes — 10 percent — before the shape-comparability filter cuts it further.

*A simulation of COVERAGE only. It invents no score, and a real list's pool would not be the roster. Read the shape of the curve, not the absolute numbers.*

## What this rules out

Growing the roster is not a path to a board. It was the obvious next move after the pilot and it does not work, because every added person brings their own unpaired years along with them.

## What it leaves

Only sources that raise DENSITY on person-years that already carry a judgment, ideally of the same shape as the one already there. That is a much narrower requirement than 'more sources', and the backlog now states it that way.

## Caveat

The 100-roster figures come from the free stages only: Wikidata records and Wikipedia list articles. No prose extraction, no scoring, no romance classification was run at that scale, so the on-screen domain is absent from the roster column and the real-life numbers are a floor rather than a final figure.
