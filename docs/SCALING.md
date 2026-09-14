# Does coverage scale with roster size?

Generated from the artifacts by `scripts/scaling_report.py`. The pilot ran 14 people; the plan's full 100-name roster was put through the same free stages. Both rosters were chosen on prominence before any check of how easy anyone is to score.

## The answer

**Coverage does not scale with roster size. A seven-fold larger roster produced 3.7x the observations and 7.7x the episodes, and the number of COMPARABLE jointly covered pairings stayed at one.**

Joint coverage is a conjunction of independently rare conditions: both people judged, near the same year, by the same kind of evidence. Each is uncommon, so the conjunction is rarer than any of them, and growing the roster multiplies the numerator and the denominator together.

## The numbers

| Metric | Pilot (14) | Roster (100) |
|---|---|---|
| Roster size | 14 | 100 |
| Relationship episodes (scorable) | 27 | 239 |
| Observations | 35 | 131 |
| People with any observation | 13 | 61 |
| Person-periods | 34 | 127 |
| Mean observations per person-period | 1.029 | 1.031 |
| Person-periods with 2+ publishers | 1 | 4 |
| Episodes with evidence on BOTH sides anywhere | — | 20 |
| Jointly covered within ±1 year | 4 | 5 |
| ...of those, COMPARABLE (same evidence shape) | 1 | 1 |

## What this rules out

Growing the roster is not a path to a board. It was the obvious next move after the pilot and it does not work, because every added person brings their own unpaired years along with them.

## What it leaves

Only sources that raise DENSITY on person-years that already carry a judgment, ideally of the same shape as the one already there. That is a much narrower requirement than 'more sources', and the backlog now states it that way.

## What a source would have to look like

"Find better sources" is not a specification, so `scripts/source_requirement.py`
turns it into one: simulate a hypothetical annual ranked list over the REAL
episode structure and the REAL roster, and count how many of the 239 scorable
episodes come out jointly covered.

| Names per year | p10 | median | p90 |
|---|---|---|---|
| 1 | 0 | 0 | 0 |
| 5 | 0 | 1 | 3 |
| 10 | 0 | 3 | 7 |
| 25 | 5 | 10 | 15 |
| 50 | 11 | 16 | 20 |
| 100 | 19 | 22 | 25 |
| 200 | 18 | 22 | 25 |
| 400 | 19 | 22 | 25 |

Read against what actually exists:

| Source | Names per year |
|---|---|
| Sexiest Man Alive | 1 |
| People Most Beautiful cover | 1 |
| Maxim Hot 100, as published on Wikipedia | 1 |
| FHM top ten, as on Wikipedia | 10 |
| FHM full list, **not available on a permitted route** | 100 |

Three readings.

**One name a year covers nothing.** Every award source this project can
currently reach sits on that rung, and the simulation puts its median at zero.
That is not a shortfall to be closed by adding more such sources.

**The requirement is about a hundred names a year.** At that depth the median
reaches 22 episodes, roughly seven times what the ten-name rung gives. That is
precisely the shape of FHM's real published list, which exists and is not
reachable: Wikipedia carries only its top ten, and the publisher blocks the AI
crawlers.

**It saturates there.** Two hundred names a year buys nothing over one hundred,
because the binding constraint becomes the roster and the era span rather than
the list depth. So the ceiling for this design, with a perfect source, is about
22 of 239 episodes — nine percent — before the shape-comparability filter cuts
it further.

## Caveat

The 100-roster figures come from the free stages only: Wikidata records and Wikipedia list articles. No prose extraction, no scoring, no romance classification was run at that scale, so the on-screen domain is absent from the roster column and the real-life numbers are a floor rather than a final figure.
