# Why this design cannot produce a board with the available evidence

Filed 2026-09-14. This is the capstone finding of the overnight run, and it is
structural rather than a shortage of data.

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
| Brad Pitt + Jennifer Aniston, 1999 | `editorial_award`, 92.0 | `ordered_rank`, 84.0 | −8.0 |
| Brad Pitt + Jennifer Aniston, 2000 | `editorial_award`, 92.0 | `ordered_rank`, 80.0 | −12.0 |
| Scarlett Johansson + Ryan Reynolds, 2009 | `ordered_rank`, 84.0 | `editorial_award`, 92.0 | +8.0 |

Every comparable gap is **exactly zero**. Every non-zero gap is
**shape-mismatched**. There are no exceptions in the corpus.

## Why that happens, and why more data will not fix it

Three facts combine into a trap.

1. **A one-winner award is superlative by construction.** The rubric correctly
   places every winner in band 90–100, and in practice every single one lands
   at 92. Repeat-scoring confirms this is not noise: an award dossier returns
   92 four times out of four, SD 0.0.
2. **The award shape is the only one common enough to match.** It is what the
   freely available sources publish — Sexiest Man Alive, People's Most
   Beautiful cover, Maxim's number one, Esquire's pick. All one name a year.
3. **Comparability requires matching shapes.** So the pairings that qualify as
   comparable are precisely the award-versus-award ones, which are precisely
   the ones pinned at 92 on both sides.

Therefore:

> **A comparable pairing is 0.0 by construction, and any gap large enough to be
> interesting is confounded by publication format.**

Adding more award-shaped sources raises coverage, creates more comparable
pairings, and every one of them will be 0.0. That is not a partial fix. It
makes the board larger and no more informative.

## What this changes about the source requirement

`docs/SOURCE-HUNT.md` concluded the project needs a source of roughly a hundred
ranked names a year. This sharpens it in a way that matters:

**The ranked depth has to exist on BOTH sides of a pairing — which, for
male-female pairings, means ranked lists covering men AND women over the same
years.**

The corpus currently has 12 `ordered_rank` observations for the pilot and 65 at
roster scale, and they are overwhelmingly women, because FHM's list is a
women's list. Every one of the mismatched pairings above is a man with an award
and a woman with a rank. A men's equivalent of FHM, over the same period, is the
missing piece — not more women's lists and certainly not more awards.

## What it does not mean

It does not mean the measurement is broken. The rubric spans 63 to 92 on
synthetic dossiers and 66 to 93 on real ones, ten distinct values each, and two
model families agree closely. The apparatus works. The evidence available to it
cannot exercise it on both halves of a couple at once.

It also does not mean the pilot was wasted. Every one of these conclusions rests
on measurements that did not exist twelve hours ago, and the trap is only
visible because the pipeline runs end to end.
