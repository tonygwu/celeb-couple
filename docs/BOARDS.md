# The four boards

Generated 2026-09-15 from `['data/roster100/run/pairing_scores.json', 'data/roster100/run/pairing_scores_fable.json']`, contract `a0f8f89e662e` (pairing-1.0).

**These are subjective model judgments, not measurements.** No source backs any number here. Plan v4 §9.

131 pairings, 119 judged, **81 with a romance to score** (centrality above zero). The rest are cast-list co-appearances and contribute nothing.

## Error bars

**100 pairings were judged by both judge families.** Mean disagreement on the gap is **0.28** points, median 0.20, worst 1.0.

So two cumulative totals closer than about **0.28** are not distinguishable. This is a better quantity than repeat noise within one family: it measures whether a judgment is a property of the rubric or of the model that happened to make it.

**Centrality disagreement matters more than gap disagreement.** The families differ on centrality for 12 of 100 pairings, and for **3** of them one family says there is no romance at all while the other says there is. A pairing that flips to zero leaves the board entirely, which moves a total further than any disagreement about the gap.

## Board 1: Men, on-screen

*How much they punched above their weight. Positive means their partners were judged more conventionally attractive than they were. Minimum 2 scored pairings.*

| # | Person | Pairings | Cumulative PAW | Rate | Biggest contributor |
|---|---|---|---|---|---|
| 1 | Adam Sandler | 3 | +4.05 | +1.50 | Jennifer Aniston (Just Go with It) +1.50 |
| 2 | Matt Damon | 2 | +1.19 | +0.95 | Angelina Jolie (The Good Shepherd) +0.81 |
| 3 | Ben Affleck | 4 | +1.07 | +0.43 | Jennifer Garner (Daredevil: The Director's Cut) +0.34 |
| 4 | Johnny Depp | 2 | +1.03 | +0.77 | Angelina Jolie (The Tourist) +1.00 |
| 5 | Brad Pitt | 2 | +0.65 | +0.33 | Angelina Jolie (By the Sea) +0.40 |
| 6 | Chris Evans | 2 | +0.07 | +0.07 | Scarlett Johansson (The Perfect Score) +0.10 |

**2 of 5 adjacent rank gaps are smaller than the 0.28 floor**, so those orderings are not established.

**Volume check.** Cumulative PAW regressed on exposure gives R² = 0.47 over 6 people, so about **47% of this cumulative board is explained by how many romances each person had**, not by who they were with. Low enough that the ordering is not merely a count.

## Board 2: Men, real life

*How much they punched above their weight. Positive means their partners were judged more conventionally attractive than they were. Minimum 2 scored pairings.*

| # | Person | Pairings | Cumulative PAW | Rate | Biggest contributor |
|---|---|---|---|---|---|
| 1 | Ben Affleck | 6 | +3.55 | +0.59 | Shauna Sexton (2018) +1.70 |
| 2 | Colin Jost | 2 | +2.55 | +1.27 | Scarlett Johansson (2020) +1.30 |
| 3 | Ojani Noa | 2 | +1.35 | +0.68 | Jennifer Lopez (1997) +0.75 |
| 4 | Kevin Costner | 4 | +0.90 | +0.23 | Elle Macpherson (1996) +0.90 |
| 5 | Brad Pitt | 2 | -0.60 | -0.30 | Angelina Jolie (2005) +0.10 |
| 6 | Chris Evans | 4 | -0.90 | -0.23 | Jessica Biel (2001) +0.40 |
| 7 | Johnny Depp | 9 | -1.40 | -0.16 | Polina Glen (2017) +1.50 |
| 8 | George Clooney | 9 | -1.75 | -0.19 | Kelly Preston (1987) +0.35 |

**0 of 7 adjacent rank gaps are smaller than the 0.28 floor**, so those orderings are not established.

**Volume check.** Cumulative PAW regressed on exposure gives R² = 0.20 over 8 people, so about **20% of this cumulative board is explained by how many romances each person had**, not by who they were with. Low enough that the ordering is not merely a count.

## Board 3: Women, on-screen

*How much they punched above their weight. Positive means their partners were judged more conventionally attractive than they were. Minimum 2 scored pairings.*

| # | Person | Pairings | Cumulative PAW | Rate | Biggest contributor |
|---|---|---|---|---|---|
| 1 | Jennifer Lopez | 2 | -0.36 | -0.60 | Richard Gere (Shall We Dance?) -0.16 |
| 2 | Scarlett Johansson | 6 | -1.79 | -0.46 | Chris Evans (The Nanny Diaries) +0.03 |
| 3 | Angelina Jolie | 7 | -3.42 | -0.70 | Jude Law (Sky Captain and the World of Tomorrow) -0.08 |
| 4 | Jennifer Aniston | 7 | -4.73 | -0.80 | Jake Gyllenhaal (The Good Girl) +0.40 |

**0 of 3 adjacent rank gaps are smaller than the 0.28 floor**, so those orderings are not established.

**Volume check.** Cumulative PAW regressed on exposure gives R² = 0.90 over 4 people, so about **90% of this cumulative board is explained by how many romances each person had**, not by who they were with. The rate column is the one to read.

## Board 4: Women, real life

*How much they punched above their weight. Positive means their partners were judged more conventionally attractive than they were. Minimum 2 scored pairings.*

| # | Person | Pairings | Cumulative PAW | Rate | Biggest contributor |
|---|---|---|---|---|---|
| 1 | Jennifer Aniston | 9 | -3.90 | -0.43 | Brad Pitt (1998) +0.70 |
| 2 | Angelina Jolie | 4 | -4.05 | -1.01 | Brad Pitt (2005) -0.10 |
| 3 | Scarlett Johansson | 3 | -4.05 | -1.35 | Colin Jost (2017) -1.25 |
| 4 | Jennifer Lopez | 7 | -7.45 | -1.06 | Ojani Noa (1996) -0.60 |

**2 of 3 adjacent rank gaps are smaller than the 0.28 floor**, so those orderings are not established.

**Volume check.** Cumulative PAW regressed on exposure gives R² = 0.07 over 4 people, so about **7% of this cumulative board is explained by how many romances each person had**, not by who they were with. Low enough that the ordering is not merely a count.

# The normalized view

**Second view. The four boards above are the default and are unchanged.**

Every absolute score is restated as its distance from the mean of its OWN sex, in units of that sex's spread, and then mapped back onto the judge family's own scale so the numbers stay in rubric points. The population is **(sex, person, period) tuples**, because a person is judged at the time of each pairing: Adam Sandler in 2011 is a different observation from Adam Sandler in 2004. 363 such observations back the 119 normalized pairings.

**What this buys and what it costs.** It buys a board on which the two sexes cannot differ on average, so no ranking is inherited from the offset. It costs the question: the mean normalized gap is zero BY CONSTRUCTION, so this view can never be asked whether the judges score women higher than men. It has assumed they do not. The raw board is the one that carries that measured offset, which is why it stays first.

Unlike a constant offset, which `tests/test_offset_invariance.py` proves cannot reorder the rate board, full normalization rescales as well as shifts and therefore CAN reorder it. The counts below are that difference, measured.

## The offset it removed, and where the zero does not hold

*The mean gap is woman minus man. Normalization forces it to zero over the WHOLE observation population. It does not force it to zero inside any subset, and on this corpus it does not: the on-screen pairings that actually score keep a positive mean, which is why one women's board below stays entirely negative.*

| Subset | Domain | Pairings | Raw mean gap | Normalized mean gap |
|---|---|---|---|---|
| every judged pairing | on-screen | 64 | +0.4813 | +0.0602 |
| every judged pairing | real life | 55 | +0.3609 | -0.0622 |
| every judged pairing | both domains | 119 | +0.4256 | +0.0036 |
| scoring pairings only (centrality above zero) | on-screen | 26 | +0.6115 | +0.2138 |
| scoring pairings only (centrality above zero) | real life | 55 | +0.3609 | -0.0622 |
| scoring pairings only (centrality above zero) | both domains | 81 | +0.4414 | +0.0264 |

## The scales

*One cell per judge family and sex, because an absolute score only means something on the scale of the judge that produced it. `*` is the family's own grand scale, which the normalized scores are mapped back onto.*

| Family | Sex | n | Mean | SD |
|---|---|---|---|---|
| astra | * | 167 | 8.716 | 0.629 |
| astra | female | 77 | 8.907 | 0.520 |
| astra | male | 90 | 8.553 | 0.670 |
| fable | * | 196 | 8.703 | 0.762 |
| fable | female | 89 | 8.963 | 0.711 |
| fable | male | 107 | 8.487 | 0.739 |

## Normalized board 1: Men, on-screen

| # | Person | Pairings | Cumulative PAW | Rate | Raw rank |
|---|---|---|---|---|---|
| 1 | Adam Sandler | 3 | +2.77 | +1.02 | 1 |
| 2 | Matt Damon | 2 | +0.71 | +0.57 | 2 |
| 3 | Johnny Depp | 2 | +0.59 | +0.44 | 4 (-1) |
| 4 | Ben Affleck | 4 | +0.01 | +0.00 | 3 (+1) |
| 5 | Brad Pitt | 2 | -0.12 | -0.06 | 5 |
| 6 | Chris Evans | 2 | -0.32 | -0.30 | 6 |

**Rank changes: 2 of 6 placements move on the cumulative board (1 of 15 pairs flip), 0 on the rate board (0 of 15 pairs flip).**

**3 of 5 adjacent rank gaps are smaller than the 0.28 floor.** The floor still applies because the normalized scores are mapped back onto the judges' own scale, so both views are in rubric points.

## Normalized board 2: Men, real life

| # | Person | Pairings | Cumulative PAW | Rate | Raw rank |
|---|---|---|---|---|---|
| 1 | Colin Jost | 2 | +1.87 | +0.93 | 2 (-1) |
| 2 | Ben Affleck | 6 | +1.02 | +0.17 | 1 (+1) |
| 3 | Ojani Noa | 2 | +0.56 | +0.28 | 3 |
| 4 | Kevin Costner | 4 | -0.85 | -0.21 | 4 |
| 5 | Brad Pitt | 2 | -1.21 | -0.61 | 5 |
| 6 | Chris Evans | 4 | -2.59 | -0.65 | 6 |
| 7 | Johnny Depp | 9 | -5.29 | -0.59 | 7 |
| 8 | George Clooney | 9 | -5.67 | -0.63 | 8 |

**Rank changes: 2 of 8 placements move on the cumulative board (1 of 28 pairs flip), 3 on the rate board (2 of 28 pairs flip).**

**0 of 7 adjacent rank gaps are smaller than the 0.28 floor.** The floor still applies because the normalized scores are mapped back onto the judges' own scale, so both views are in rubric points.

## Normalized board 3: Women, on-screen

| # | Person | Pairings | Cumulative PAW | Rate | Raw rank |
|---|---|---|---|---|---|
| 1 | Jennifer Lopez | 2 | -0.20 | -0.33 | 1 |
| 2 | Scarlett Johansson | 6 | -0.33 | -0.08 | 2 |
| 3 | Angelina Jolie | 7 | -1.74 | -0.36 | 3 |
| 4 | Jennifer Aniston | 7 | -1.91 | -0.32 | 4 |

**Rank changes: 0 of 4 placements move on the cumulative board (0 of 6 pairs flip), 3 on the rate board (2 of 6 pairs flip).**

**Sign check.** 4 of 4 women were negative on the raw cumulative board; 4 of 4 are negative here.

Every one of them is still negative, so the raw board's uniform sign is not only the mirror of the offset. The offset table above says why: the mean gap on the scoring pairings in this domain is still positive after normalization.

**2 of 3 adjacent rank gaps are smaller than the 0.28 floor.** The floor still applies because the normalized scores are mapped back onto the judges' own scale, so both views are in rubric points.

## Normalized board 4: Women, real life

| # | Person | Pairings | Cumulative PAW | Rate | Raw rank |
|---|---|---|---|---|---|
| 1 | Jennifer Aniston | 9 | +0.00 | +0.00 | 1 |
| 2 | Angelina Jolie | 4 | -2.50 | -0.62 | 2 |
| 3 | Scarlett Johansson | 3 | -2.93 | -0.98 | 3 |
| 4 | Jennifer Lopez | 7 | -4.72 | -0.67 | 4 |

**Rank changes: 0 of 4 placements move on the cumulative board (0 of 6 pairs flip), 0 on the rate board (0 of 6 pairs flip).**

**Sign check.** 4 of 4 women were negative on the raw cumulative board; 3 of 4 are negative here.

Jennifer Aniston crosses to zero or above. The crossing is smaller than the 0.28 floor for Jennifer Aniston, so the sign changes but the change is not distinguishable from zero.

**0 of 3 adjacent rank gaps are smaller than the 0.28 floor.** The floor still applies because the normalized scores are mapped back onto the judges' own scale, so both views are in rubric points.

## What normalization did, in one table

| Board | People | Cumulative: moved | pairs flipped | Rate: moved | pairs flipped |
|---|---|---|---|---|---|
| 1: Men, on-screen | 6 | 2 | 1/15 | 0 | 0/15 |
| 2: Men, real life | 8 | 2 | 1/28 | 3 | 2/28 |
| 3: Women, on-screen | 4 | 0 | 0/6 | 3 | 2/6 |
| 4: Women, real life | 4 | 0 | 0/6 | 0 | 0/6 |
| **All four** | **22** | **4** | **2/55** | **6** | **4/55** |

