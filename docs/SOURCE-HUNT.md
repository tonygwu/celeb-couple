# The source hunt, and what it concluded

Filed 2026-09-14 by the overnight run. This records a **negative result**, so
that nobody spends another night re-searching the same surfaces.

## The requirement, stated precisely

`scripts/source_requirement.py` simulates a hypothetical annual ranked list over
the real episode structure and the real 100-name roster. The curve:

| Names per year | Episodes jointly covered (median of 239) |
|---|---|
| 1 | 0 |
| 10 | 4 |
| 25 | 13 |
| 50 | 23 |
| 100 | 25 |
| 200 | 25 (saturates) |

*Corrected 2026-09-14.* The simulation drew its annual list WITH replacement,
so a rung labelled "100 names" listed a median of 48 distinct people and no
rung above it listed more — the saturation was partly the sampler rather than
the coverage problem. A published ranked list of 100 has 100 distinct names, so
it now samples without replacement. The curve rises more steeply and still
saturates at 100, this time because the roster is exhausted. The conclusion is
unchanged and now rests on the right mechanism.

So the product needs **an annual list of roughly a hundred names**, covering the
roster's population and era, on a route this project may use. One name a year
covers nothing, and beyond a hundred there is no further gain.

**That requirement does not depend on the simulation's invented popularity
weighting.** The model weights names as 1/(i+3) so that prominent people recur
across years, which is a guess. Re-running at bound 1 under a uniform weighting
and under a much steeper 1/(i+1)² gives:

| Names per year | 1/(i+3) | uniform | 1/(i+1)² |
|---|---|---|---|
| 10 | 4 | 6 | 1.5 |
| 25 | 13 | 17 | 8 |
| 50 | 23 | 25 | 17 |
| 100 | **25** | **25** | **25** |
| 200 | **25** | **25** | **25** |

All three converge at a hundred names a year and stay converged, because at
that depth every scheme lists the whole roster and the weighting stops
mattering. The weighting only moves the shallow rungs — which no real source
occupies.

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

## The men's ranked list, specifically

`docs/THE-TRAP.md` narrowed the requirement further: the ranked depth has to
exist on BOTH sides of a pairing, and for male-female pairings that means a
men's ranked list over the same years as the women's one. Every mismatched
pairing in the corpus is a man with an award and a woman with a rank, because
FHM's list is a women's list.

Searched specifically for one on 2026-09-14, across eight query formulations.
Wikipedia has no men's equivalent: the only list-shaped articles returned were
a women's list (FHM), a music chart (Triple J Hottest 100), and a
non-ranking roster (List of male underwear models).

Men's ranked lists do exist. GLAMOUR UK published ranked "Sexiest Men" results
for 2010, 2011 and 2012, running to 50, 70 and 100 places. Condé Nast blocks the
AI agents **and** `archive.org_bot`, so neither the live pages nor the archive
is a route this project may use.

So the two halves of the requirement fail in different ways. Women's ranked
depth exists and is truncated on the permitted surface (Wikipedia carries FHM's
top ten of a hundred). Men's ranked depth exists and is not on the permitted
surface at all.

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

## IMDb: the bulk datasets, admitted 2026-09-15

**Plan v3 §3 listed IMDb as `Out`. The operator reversed that on 2026-09-15,
for full use including the published page.** The reversal is recorded here
because this file, not the plan, is what an agent reads before fetching
anything.

### What the restriction was

Plan v3's source matrix gave one reason: IMDb's terms permit the bulk datasets
for personal and non-commercial use, and forbid data "repurposed to create any
kind of online/offline database of movie information". A public leaderboard
built from the dumps is arguably that database. The restriction was never a
crawler question. The bulk files are the one IMDb route with no robots.txt
issue at all, because they are published for download.

### What was decided instead

Full use. The dumps may drive roster construction, pairing discovery, and the
film titles and years shown on the board. The concern above was put to the
operator with that cost named, and the operator chose this option anyway. It is
their call and it is deliberate, not an oversight.

### What did NOT change

The restricted publishers are untouched and stay untouched: **People Inc. /
people.com, Ziff Davis / askmen.com, Maxim, Condé Nast / Glamour.** Never
fetched, by any route, archives included. IMDb was never on that list; it sat
in the plan's matrix for an unrelated reason.

### Operating rules for the dumps

- The `.tsv.gz` files are **never committed**. They are ~2 GB and they are not
  ours to redistribute. Point the loader at a local path.
- Derived artifacts commit normally. A pairing graph is our output.
- `title.principals` carries `category`, which is `actor` or `actress`. That is
  the sex signal the board needs, and it comes from the file rather than from
  an inference over names.
