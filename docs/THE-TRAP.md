# Why this design cannot produce a board with the available evidence

Filed 2026-09-14. This is the capstone finding of the overnight run, and it is
structural rather than a shortage of data.

## The part that matters most: the confound is aligned with gender

Sourcing partner gender from Wikidata turned the shape confound into something
sharper. The evidence shapes are not distributed evenly across the sexes. They
are almost perfectly separated.

| | `editorial_award` | `ordered_rank` | `unordered_inclusion` |
|---|---|---|---|
| **male** | 8 | **0** | 1 |
| **female** | 12 | **17** | 3 |

**Men in this corpus hold zero ranked observations. Women hold 17.**

An award pins near the top of the scale by construction; a ranked placement does
not. So the imbalance shows up directly in the estimates:

| | n | mean | SD | range |
|---|---|---|---|---|
| male | 8 | **90.75** | 4.89 | 78.0–94.0 |
| female | 31 | **87.1** | 6.49 | 64.0–94.0 |

**The male mean sits 4.23 points above the female mean before any fact about
any individual enters**, and removing any single male person entirely moves
that between 2.9 and 5.3 — it never approaches zero and never reverses, so it
is not one person carrying it, and the male estimates are compressed (SD 4.89 against 6.49) because five of the eight are exactly 92.

A four-view product compares a man against a woman in every row. With shapes
distributed this unevenly, the sign of a typical gap is decided by which sex
somebody is rather than by what the judgments said. That is not a subtle
statistical caveat; it is the measurement reporting a property of how magazines
publish as though it were a finding about couples.

It is also why the Brad Pitt and Jennifer Aniston gaps of −6 and −14 must not be
read as results. He is judged by an award, she by ranked placements, and that
alone accounts for a large part of the sign and the size.

## The observation

Across the pilot and the 100-name roster, every jointly covered pairing the
project can produce falls into exactly two groups.

**Comparable pairings — both sides judged by the same kind of evidence:**

| Pairing | A | B | Gap |
|---|---|---|---|
| Daredevil, 2003 | Ben Affleck, `editorial_award`, 92.0 | Jennifer Garner, `editorial_award`, 92.0 | **0.0** |
| Richard Gere + Cindy Crawford, 1992 | `editorial_award`, 92.0 | `editorial_award`, 92.0 | **0.0** |

**Shape-mismatched pairings — an award against a ranked placement:**

| Pairing | A | B | Gap |
|---|---|---|---|
| Brad Pitt + Jennifer Aniston, 1999 | `editorial_award`, 92.0 | `ordered_rank`, 86.0 | −6.0 |
| Brad Pitt + Jennifer Aniston, 2000 | `editorial_award`, 92.0 | `ordered_rank`, 78.0 | −14.0 |
| Brad Pitt + Jennifer Aniston, 2001 | `editorial_award`, 92.0 | `ordered_rank`, 78.0 (reused from 2000) | −14.0 |
| Scarlett Johansson + Ryan Reynolds, 2009 | `ordered_rank`, 84.0 | `editorial_award`, 92.0 | +8.0 |

The Johansson–Reynolds row comes from the 100-name roster run and the rest from
the pilot. Those are two separate scoring runs, which matters: see "The numbers
in this table are not stable to two points" below.

Every comparable gap is **exactly zero**. Every non-zero gap is
**shape-mismatched**. There are no exceptions in the corpus.

`scripts/verify_trap.py` re-derives those two statements and the gender claim
below from the artifacts, and runs in `bash scripts/run_chain.sh reports`. It
exits non-zero if any of them stops holding. **A break would be good news** —
a comparable pairing with a real gap, or a man carrying ranked evidence, is the
signal this project has not been able to produce — which is exactly why it must
fail loudly rather than sit here being quoted.

### The numbers in this table are not stable to two points

The Pitt–Aniston rows come from the pilot run and the Johansson–Reynolds row
from the roster run. Three person-periods were scored in BOTH runs, on
byte-identical dossiers, under the same contract id, by the same judge family.
One returned the same estimate and two moved by 2.0 points:

| Person | Period | Shape | pilot | roster | Delta |
|---|---|---|---|---|---|
| Brad Pitt | 2000 | `editorial_award` | 92.0 | 92.0 | +0.0 |
| Jennifer Aniston | 1999 | `ordered_rank` | 86.0 | 84.0 | +2.0 |
| Jennifer Aniston | 2000 | `ordered_rank` | 78.0 | 80.0 | −2.0 |

The award held still and both ranks moved, which is the same split the repeat
measurement found. It also means the published least significant difference of
1.2 points was too small: it pooled the award dossiers' zero measured variance
with the ranked ones', halving it. Quoted per shape, over four ranked dossiers
repeated four times each, the rank-shaped LSD was **2.56 points**.

*Measured again 2026-09-15* with both judge families on the same four dossiers:
**1.03 points**. Do not read that as a sharper floor. fable's own mean
within-judge sd was 0.926 on the first run and 0.269 on the second, a 3.4x
difference in the noise measurement itself, so four dossiers at four repeats
does not pin this quantity. Both numbers are recorded and every conclusion here
holds against either.

*Corrected twice, 2026-09-14.* The pooled figure was 1.2. Quoting it per shape
gave 2.22. That still used `pstdev`, the POPULATION standard deviation, on four
runs — but four runs are a sample of the rating process, not the whole of it,
and the population formula underestimates the population SD by about 13% at
n = 4. The sample standard deviation gives 2.56. Every conclusion below held at
all three figures.

Which dossiers move is itself the finding. All four ranked dossiers moved
between repeats, with SDs of 0.5, 0.71, 1.0 and 1.0. Both award dossiers
returned 92 eight times out of eight. The shape that pins is also the shape
that holds still, and the shape that discriminates is the shape that wobbles.

None of this changes the conclusion below. The comparable gap is 0.0 and the
noise floor is now known to be higher, so it is even less distinguishable from
zero. What it changes is how any single gap in the table above should be read:
a −6 could have been a −4.

## Why that happens, and why more data will not fix it

Three facts combine into a trap.

1. **A one-winner award is superlative by construction**, so it concentrates
   on one value. Of 18 award-shaped estimates, **15 land at exactly 92**; the
   other three are 78, 91 and 94. The 16 rank-shaped estimates spread across
   **nine** distinct values from 64 to 93. That contrast is the mechanism:
   awards agree with each other because there is only one thing an award can
   say, and ranks disagree because a rank carries a degree.

   Repeat-scoring is consistent with this. Two award dossiers returned 92 on
   every one of eight repeats. That is **not** proof of zero variance —
   identical draws from a low-variance process look exactly like draws from a
   zero-variance one — and no figure is quoted for that shape.
2. **The award shape is the only one common enough to match.** It is what the
   freely available sources publish — Sexiest Man Alive, People's Most
   Beautiful cover, Maxim's number one, Esquire's pick. All one name a year.
3. **Comparability requires matching shapes.** So the pairings that qualify as
   comparable are precisely the award-versus-award ones, which are precisely
   the ones pinned at 92 on both sides.

Therefore:

> **A comparable pairing is almost always 0.0 by construction, and any gap
> large enough to be interesting is confounded by publication format.**

Adding more award-shaped sources raises coverage and creates more comparable
pairings, and most of them will be exactly 0.0 — 15 of the 18 award-shaped
estimates in this corpus land on the same value, so two of them drawn at random
agree about seven times in ten. That is not a partial fix. It makes the board
larger and very little more informative.

*Corrected 2026-09-14.* This said "every one of them will be 0.0", which was
true when every award-shaped estimate was 92 and stopped being true when the
corpus grew: the three exceptions are 78, 91 and 94. An award-versus-award
pairing CAN produce a non-zero gap. It is rare, and it does not rescue the
design, but the argument does not need the absolute and should not make it.

## Does any of this depend on the choices that were made?

Three of these conclusions rest on methodological choices that could
defensibly have gone the other way: the ±1 nearby-period bound, the romance
filter on co-starring films, and enforcing shape comparability rather than
labelling it. Each was argued in the plan. None had been tested for whether the
conclusion needs it.

`scripts/conclusion_robustness.py` re-derives the two structural claims at every
setting of the bound from 0 to 4, with and without the romance filter — ten
settings in all, reusing the same estimates throughout.

**The claims hold at nine of the ten.** The one failure is at bound 4 with the
romance filter OFF, and its single counterexample is *Thor: Love and Thunder*
2022 with a gap of +3 — a film co-appearance that was never established as a
romance, scored from estimates four years away from the year in question.

That is the setting this project argues against on both dials at once, and it
takes both to produce one counterexample worth three points. The conclusions
are a property of the evidence, not of the dials.

*What this does not test:* every setting reuses the SAME estimates. It shows the
conclusions do not depend on the three choices. It says nothing about whether
they survive different evidence, which is what a men's ranked list would
provide and what `docs/SOURCE-HUNT.md` concluded is unreachable.

## What this changes about the source requirement

`docs/SOURCE-HUNT.md` concluded the project needs a source of roughly a hundred
ranked names a year. This sharpens it in a way that matters:

**The ranked depth has to exist on BOTH sides of a pairing — which, for
male-female pairings, means ranked lists covering men AND women over the same
years.**

The corpus currently has 17 `ordered_rank` observations for the pilot and 65 at
roster scale, and they are overwhelmingly women, because FHM's list is a
women's list. Every one of the mismatched pairings above is a man with an award
and a woman with a rank. A men's equivalent of FHM, over the same period, is the
missing piece — not more women's lists and certainly not more awards.

## The missing piece, searched for and not found

Searched specifically on 2026-09-14 for a men's ranked list on a permitted
route. Wikipedia has none: eight query formulations returned a women's list, a
music chart, and a roster of underwear models.

They exist off the permitted surface. GLAMOUR UK ran ranked Sexiest Men results
for 2010, 2011 and 2012, to 50, 70 and 100 places. Condé Nast blocks the AI
agents and `archive.org_bot` alike, so neither the live page nor the archive is
usable here.

That is the whole trap in one sentence: **the evidence that would break it is
published, and every route to it is closed.**

## What it does not mean

It does not mean the measurement is broken. The rubric spans 63 to 92 on
synthetic dossiers and 64 to 94 on real ones, ten distinct values on the
synthetic corpus and twelve on the real one. Two model families agree closely
on the SYNTHETIC corpus; on the real dossiers only one family ran, because
codex reached 0% of its quota window mid-run, so cross-family agreement there
is unmeasured. The apparatus works. The evidence available to it cannot
exercise it on both halves of a couple at once.

It also does not mean the pilot was wasted. Every one of these conclusions rests
on measurements that did not exist twelve hours ago, and the trap is only
visible because the pipeline runs end to end.
