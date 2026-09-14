# The source hunt, and what it concluded

Filed 2026-09-14 by the overnight run. This records a **negative result**, so
that nobody spends another night re-searching the same surfaces.

## The requirement, stated precisely

`scripts/source_requirement.py` simulates a hypothetical annual ranked list over
the real episode structure and the real 100-name roster. The curve:

| Names per year | Episodes jointly covered (median of 239) |
|---|---|
| 1 | 0 |
| 10 | 3 |
| 25 | 10 |
| 50 | 16 |
| 100 | 22 |
| 200 | 22 (saturates) |

So the product needs **an annual list of roughly a hundred names**, covering the
roster's population and era, on a route this project may use. One name a year
covers nothing, and beyond a hundred there is no further gain.

## Every surface checked, and what it holds

| Surface | Depth found | Verdict |
|---|---|---|
| Wikipedia: People (magazine), Sexiest Man Alive | 1 winner/year, 1985–2025 | usable, no depth |
| Wikipedia: People, Most Beautiful cover | 1/year, 1990–2026 | usable, no depth |
| Wikipedia: People, Sexiest Woman Alive | **1 entry, ever** (2014) | negligible |
| Wikipedia: Maxim (magazine), Hot 100 | 1 winner/year, 2000–2025 | usable, no depth |
| Wikipedia: Esquire, Sexiest Woman Alive | 1/year, 2005–2015 | usable, no depth |
| Wikipedia: FHM's 100 Sexiest Women (UK) | **top ten per year**, 1995–2017 | the deepest permitted source found |
| Wikipedia: biographical prose | ~1 mention per person-year | useful for density, not depth |
| Wikipedia: categories | `Category:People Sexiest Man Alive` — winners only | no depth |
| Wikipedia: navboxes | `Template:Maxim Hot 100` — the 24 winners | no depth |
| Wikidata: structured awards (P166) | **no appearance-related award at all** among 60 awards the roster holds | nothing |
| people.com, askmen.com | full lists exist | **terms forbid LLM extraction and dataset creation** |
| maxim.com, glamourmagazine.co.uk | full lists exist | **AI crawlers disallowed** |
| Wayback captures of the above | some editions exist | archiving conveys no reuse permission |

## The conclusion

**The source this product needs exists, and is not reachable.**

FHM publishes exactly the shape required — a hundred ranked names a year, over
two decades. Wikipedia carries only its top ten. The publisher blocks the AI
crawlers. Every other permitted surface tops out at one name a year, which the
simulation puts at zero coverage.

This is not a gap that more searching closes. It is a property of how
attractiveness lists are published and licensed: the ranking IS the product, so
the publishers keep it, and the free encyclopaedic surfaces record only the
winner.

## What would change it

1. **A licence or permission from a publisher** holding a deep annual list.
   This is a commercial conversation, not an engineering task.
2. **A permitted source nobody has found**, with ~100 names a year over a long
   span, covering the roster's population. The surfaces above are what was
   checked; this is not a proof of non-existence.
3. **Changing the product** so it does not need joint coverage of two people in
   the same year. That is the operator's call and is out of scope for a night's
   work, but it is the only one of the three that is fully within our control.

## What NOT to do

- Do not add more one-name-a-year award sources. The simulation puts that rung
  at zero, and each one makes the shape confound worse rather than better.
- Do not widen the nearby-period bound to force coverage. It buys two pairings
  and costs the meaning of the estimate.
- Do not select the roster to fit the evidence. The 100-name roster was chosen
  on prominence before any scorability check, deliberately, and rebuilding it
  around FHM's coverage would manufacture a board out of a sampling choice.
