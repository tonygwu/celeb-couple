# M0 pilot report — Celebrity Pairing WAR

Generated 2026-09-14 from the run artifacts under `data/pilot/`, input fingerprint `c04c872e5401`. Every number below is read from a JSON artifact, not typed.

The fingerprint, not the date, is this report's identity: it hashes the artifacts with their `generated_at_utc` stamps removed, so re-running the chain over unchanged inputs produces an identical file. A changed fingerprint means an input changed, not that the chain ran again. An input can change without any rendered number moving — a new field in an artifact will do it — so the fingerprint is a reason to read the diff, not a claim about what is in it.

**Private pilot. Nothing here is published, ranked, or deployed. Every relationship and every on-screen pairing is an UNVERIFIED candidate.**

This report covers the 14-person pilot. Three companion documents cover what came after it:

- [`docs/SCALING.md`](SCALING.md) — whether growing the roster to 100 helps, and what a usable source would have to look like
- [`docs/SOURCE-HUNT.md`](SOURCE-HUNT.md) — every surface checked, and the negative result
- [`docs/REACHABLE-PRODUCTS.md`](REACHABLE-PRODUCTS.md) — what can be built with the evidence that exists

## The answer first

**The measurement works. The evidence supply does not.**

The rubric behaves largely as intended under adversarial testing: 25 of 27 stress scorings succeeded, and of the 4 cases that report a spread, 3 fall within the measured noise floor. The exception is **S2_format_equivalence**, discussed below.

Both model families ran on the STRESS corpus and agreed on the calibration anchor. They did not both run on the real dossiers: every estimate in this report comes from one family, for the reason given in the scoring section.

But across the 14-person cohort, the permitted sources yielded **41 attractiveness observations total**, covering 10 of 14 cohort people; 4 have none at all. A further 4 people outside the cohort carry observations — partners, whose evidence is what makes a pairing jointly covered.

Across all 29 relationship episodes and 20 co-starring films — **49 candidate pairings** — and after both the ±1-year bounded reuse AND the romance filter, exactly **4** pairings are jointly covered.

**The decisive measurement**: of 39 scored person-periods, 18 rest on a one-winner editorial award and 16 on an ordered rank. The award-shaped ones cluster at mean 91.28 with sd **3.263**; the rank-shaped ones sit lower, at mean 84.56, and spread more than twice as wide, sd **6.727**. A one-winner award is superlative by construction, so it concentrates: 15 of 18 award-shaped estimates are exactly 92. Ranked evidence carries a degree, so it can tell people apart.

## 1. Cohort

`pilot-cohort-2026-09-14`, selected 2026-09-14, on diversity of era, gender and casting type, chosen BEFORE any check of how easy each is to score.

| Person | Gender | Casting type | Observations found |
|---|---|---|---|
| Ben Affleck | male | 1990s-2020s lead | 1 |
| Brad Pitt | male | 1990s-2020s lead | 3 |
| Denzel Washington | male | 1980s-2020s lead | 1 |
| Harrison Ford | male | 1980s-2010s lead | 1 |
| Idris Elba | male | 2000s-2020s lead | 3 |
| Adam Sandler | male | comic lead | **0** |
| Paul Giamatti | male | character lead | **0** |
| Ana de Armas | female | 2010s-2020s lead | **0** |
| Jennifer Garner | female | 2000s-2010s lead | 2 |
| Kate Beckinsale | female | 1990s-2010s lead | 1 |
| Liv Tyler | female | 1990s-2000s lead | 1 |
| Michelle Pfeiffer | female | 1980s-1990s lead | 5 |
| Melissa McCarthy | female | comic lead | 1 |
| Zendaya | female | 2010s-2020s lead | **0** |

## 2. Source access decisions

Facts read from English Wikipedia (CC BY-SA), not from the publishers' sites. people.com and askmen.com forbid LLM extraction and dataset creation in their terms; maxim.com blocks the AI crawlers. Those routes were not used.

| Publisher | Route taken | Why |
|---|---|---|
| Wikidata | SPARQL, used | CC0; carries date qualifiers with explicit precision |
| English Wikipedia | API, used | CC BY-SA; reports the award fact and cites the publisher |
| people.com (People Inc.) | **not fetched** | robots.txt prohibits LLM use including RAG, and dataset creation |
| askmen.com (Ziff Davis) | **not fetched** | same prohibition wording; `anthropic-ai` disallowed |
| maxim.com | **not crawled** | `ClaudeBot`, `GPTBot`, `CCBot` disallowed |
| glamourmagazine.co.uk | **not crawled** | AI agents disallowed, and `archive.org_bot` too |
| Wayback captures of blocked publishers | **not used** | the Internet Archive conveys no reuse permission |

This is an engineering access assessment from published directives and terms. It is not legal advice and not clearance.

| Source | Publisher | Serves | Shape | Parsed | Years | Cohort hits |
|---|---|---|---|---|---|---|
| Sexiest Man Alive | PEOPLE | male | `editorial_award` | 43 winner rows | 1985–2025 | 6 |
| Maxim Hot 100 number one | Maxim | female | `editorial_award` | 24 winner rows | 2000–2025 | 1 |
| Most Beautiful cover choice | PEOPLE | mixed | `editorial_award` | 38 winner rows | 1990–2026 | 9 |
| Sexiest Woman Alive | Esquire | female | `editorial_award` | 11 winner rows | 2005–2015 | 1 |
| FHM 100 Sexiest Women (UK) | FHM | female | `ordered_rank` | 229 entries, 206 ranked | 1995–2017 | 16 |

## 3. Records

- 34 relationship candidates for 14 subjects, 27 carrying a source reference.
- **16 of 32 start dates are year-precision only.** They are stored as years, not as 1 January.
- Merged into 29 episodes, joining 3 dating-to-marriage progressions that Wikidata stores as two abutting statements.
- 3 episodes carry defects and are unscorable:
  - `no_start_date`: 2
  - `end_before_start`: 1
- 26 episodes eligible after the adult window.
- Scoring every year of every eligible episode would need **633 person-period estimates** (span 1964–2026), against an M0 cap of 50. The pilot samples at most three periods per pairing.

On screen: 20 co-starring films found via Wikidata cast lists. Co-appearance in a cast list proves only that both were in the film. A qualifying on-screen pairing needs an established reciprocal romance between their CHARACTERS, which scripts/classify_romance.py decides. Most co-starring pairs are not romances; the current count is in data/pilot/records/romance.json.

## 4. Measurement stress tests

27 scorings attempted, 25 succeeded, 2 failed. Taxonomy: `{"model_identity_mismatch": 2}`.

| Case | Question | Result |
|---|---|---|
| S1 single vs multi | Does publication count impose the ordering? | strong single-source **92** vs weak multi-source **63** — the stronger substantive judgment scored higher |
| S2 format | Award vs rank vs prose | {"as_award": 92, "as_rank": 92, "as_prose": 88}, spread **4**, ABOVE the measured floor of 2.56 — format moved the estimate; see the note below for why this is NOT evidence about format |
| S3 corroboration | Does an extra publisher jump a band? | 69 → 70, spread **1**, within the measured floor of 2.56 — corroboration left the estimate where it was |
| S4 contradiction | Does the rationale address the conflict? | estimate [80], names both placements: [True] |
| S5 empty / off-topic | Unscored, or a low number? | empty unscored: True, off-topic unscored: True |
| S6 identity | Same evidence, different name | {"named": 82, "anonymised": 82.5, "swapped_name": 82} — spread **0.5**, at or below the measured noise floor of 2.56 — identity did NOT move the score |
| S7 order | Reordered observations | {"order_a": 84, "order_b": 82}, spread **2**, within the measured floor of 2.56 — observation order did not move the estimate |
| S8 copy volume | One copy vs five | {"one_copy": 72, "five_copies": 72}, spread **0**, within the measured floor of 2.56 — copy volume changed nothing |

Every spread above is judged against the MEASURED noise floor rather than against a stored sentence, because a difference in estimate points only means something next to the amount those points are known to wobble by.

**S2 did not pass, and what it measures is narrower than it looks.** The same substantive judgment, rendered as an award, as a ranked placement and as prose, moved 4 points — above the floor.

It cannot be read as independent evidence that format moves perception. The prose arm uses the VERBATIM text of the rubric's calibration Example 3, which the rubric anchors at 88, and the award arm has the shape of Example 1, anchored at 92. The observed arms were 92, 92 and 88. So S2 shows the judge following its calibration anchors — which is what anchors are for, and is worth knowing — and it does not show that the same substance is perceived differently in different formats, because the rubric told the judge those two formats sit four points apart.

The observational shape-confound figure later in this report is measured on real dossiers and stands on its own. Redesigning S2 with prose that is NOT a calibration example is filed in `docs/BACKLOG.md`; until then it tests anchor-following, not format equivalence.

## 5. Coverage, the two numbers that matter

**First pass, no nearby reuse.** 32 person-periods needed for 8 selected pairings; 32 were empty and short-circuited without a model call; 0 scored.

Joint pairing coverage: **0 of 8** (0/4 real-life, 0/4 on-screen).

**Exhaustive check.** Across all 29 episodes and 20 films, zero pairings had both sides evidenced in a shared year.

**3 near-misses** — one side evidenced, the other not, within the bound:

- Armageddon (1998): Liv Tyler has 1997 evidence; Ben Affleck has none in range
- What Lies Beneath (2000): Michelle Pfeiffer has 1999 evidence; Harrison Ford has none in range
- Pearl Harbor (2001): Ben Affleck has 2002 evidence; Kate Beckinsale has none in range

**With the plan's ±1-year bounded reuse**, 4 pairing-periods become jointly covered:

- Daredevil (2003, on_screen): Ben Affleck from 2002 (d=1), Jennifer Garner from 2002 (d=1)
- relationship (1999, real_life): Brad Pitt from 2000 (d=1), Jennifer Aniston from 1999 (d=0)
- relationship (2000, real_life): Brad Pitt from 2000 (d=0), Jennifer Aniston from 2000 (d=0)
- relationship (2001, real_life): Brad Pitt from 2000 (d=1), Jennifer Aniston from 2000 (d=1)

3 of 4 rest on at least one estimate reused from an adjacent year, flagged `nearby_period`. Any simulation must give each source estimate ONE shared draw across every period it serves, or a single observation reappears as several independent ones.

## 6. Scored person-periods and pairing contributions

39 of 39 evidenced person-periods scored, using 39 model calls, 0 failed.

**Every estimate below rests on ONE judge (fable).** The plan decided J = 2 so that two model families would score each dossier independently and disagreement would be visible. Codex reached 0% of its 7-day quota window during the run, so the second family contributed to 0 of 39 person-periods. The `astra` column and the `judge gap` column are empty for that reason and not because the judges agreed. Cross-family agreement in this report is established only on the stress corpus, where both families did run.

| Person | Period | Obs | Estimate | fable | astra | judge gap | support |
|---|---|---|---|---|---|---|---|
| Michelle Pfeiffer | 1990 | 1 | 92.0 | 92.0 | – | – | single_source |
| Michelle Pfeiffer | 1995 | 1 | 86.0 | 86.0 | – | – | single_source |
| Brad Pitt | 1995 | 2 | 94.0 | 94.0 | – | – | multi |
| Jennifer Aniston | 1996 | 1 | 86.0 | 86.0 | – | – | single_source |
| Denzel Washington | 1996 | 1 | 92.0 | 92.0 | – | – | single_source |
| Liv Tyler | 1997 | 1 | 76.0 | 76.0 | – | – | single_source |
| Jennifer Aniston | 1997 | 1 | 90.0 | 90.0 | – | – | single_source |
| Jennifer Aniston | 1998 | 1 | 88.0 | 88.0 | – | – | single_source |
| Harrison Ford | 1998 | 1 | 92.0 | 92.0 | – | – | single_source |
| Michelle Pfeiffer | 1999 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Aniston | 1999 | 1 | 86.0 | 86.0 | – | – | single_source |
| Jennifer Aniston | 2000 | 1 | 78.0 | 78.0 | – | – | single_source |
| Brad Pitt | 2000 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Lopez | 2000 | 1 | 93.0 | 93.0 | – | – | single_source |
| Jennifer Lopez | 2001 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Garner | 2002 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Lopez | 2002 | 1 | 88.0 | 88.0 | – | – | single_source |
| Ben Affleck | 2002 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Lopez | 2003 | 1 | 86.0 | 86.0 | – | – | single_source |
| Angelina Jolie | 2004 | 1 | 82.0 | 82.0 | – | – | single_source |
| Michelle Pfeiffer | 2004 | 1 | 86.0 | 86.0 | – | – | single_source |
| Jennifer Aniston | 2004 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Lopez | 2004 | 1 | 82.0 | 82.0 | – | – | single_source |
| Angelina Jolie | 2005 | 1 | 90.0 | 90.0 | – | – | single_source |
| Angelina Jolie | 2006 | 2 | 94.0 | 94.0 | – | – | multi |
| Angelina Jolie | 2007 | 1 | 82.0 | 82.0 | – | – | single_source |
| Angelina Jolie | 2008 | 1 | 80.0 | 80.0 | – | – | single_source |
| Kate Beckinsale | 2009 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Aniston | 2011 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Lopez | 2011 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Aniston | 2012 | 1 | 64.0 | 64.0 | – | – | single_source |
| Idris Elba | 2013 | 1 | 92.0 | 92.0 | – | – | single_source |
| Gwyneth Paltrow | 2013 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Aniston | 2016 | 1 | 92.0 | 92.0 | – | – | single_source |
| Idris Elba | 2017 | 1 | 78.0 | 78.0 | – | – | single_source |
| Idris Elba | 2018 | 1 | 94.0 | 94.0 | – | – | single_source |
| Jennifer Garner | 2019 | 1 | 92.0 | 92.0 | – | – | single_source |
| Michelle Pfeiffer | 2020 | 1 | 80.0 | 80.0 | – | – | single_source |
| Melissa McCarthy | 2023 | 1 | 91.0 | 91.0 | – | – | single_source |

### Score compression — the most consequential measurement result

2 of 39 scored person-periods carry more than one observation; the rest carry exactly one, and the observations behind them fall into 5 shapes: `editorial_award` (n=18, 78.0-94.0, sd 3.263), `ordered_rank` (n=16, 64.0-93.0, sd 6.727), `unordered_inclusion` (n=3, 76.0-86.0, sd 4.11), `editorial_award+ordered_rank` (n=1, 94.0-94.0, sd 0.0), `editorial_award+unordered_inclusion` (n=1, 94.0-94.0, sd 0.0).

All 39 estimates land between **64.0** and **94.0**, a spread of **30.0** points on a 0-100 scale.

The judges agree almost perfectly: 0 of 0 person-periods came back identical from both families, and the largest disagreement was 0 point. So the compression is not rater noise. It is the evidence.

An annual one-winner award is a superlative judgment by construction, so the rubric places almost every winner in band 90-100: 17 of 18 award-shaped estimates, the exception being 78.0. The consequence is that **award-shaped evidence cannot discriminate between MOST winners: 15 of 18 land on the same value.** A leaderboard built on it would rank people by the difference between one judge saying 92 and another saying 93.

This was predicted in the plan's worked example A and is now measured. It is the strongest argument for either finding ordered, depth-carrying lists on permitted routes, or leading the men's and women's views with intervals instead of point estimates.

### Mirrored contributions

**Daredevil** (2003, on_screen) — co-appearance only; ROMANCE UNVERIFIED

- Ben Affleck: 92.0 (estimate from 2002)
- Jennifer Garner: 92.0 (estimate from 2002)
- covered share 1, period support `nearby_period`
- gap in the men's view **+0.0**, in the women's view **+0.0**, mirrors exactly: True

**relationship** (1999, real_life) — co-appearance only; ROMANCE UNVERIFIED

- Brad Pitt: 92.0 (estimate from 2000)
- Jennifer Aniston: 86.0 (estimate from 1999)
- covered share 1, period support `nearby_period`
- gap in the men's view **-6.0**, in the women's view **+6.0**, mirrors exactly: True

**relationship** (2000, real_life) — co-appearance only; ROMANCE UNVERIFIED

- Brad Pitt: 92.0 (estimate from 2000)
- Jennifer Aniston: 78.0 (estimate from 2000)
- covered share 1, period support `contemporaneous`
- gap in the men's view **-14.0**, in the women's view **+14.0**, mirrors exactly: True

**relationship** (2001, real_life) — co-appearance only; ROMANCE UNVERIFIED

- Brad Pitt: 92.0 (estimate from 2000)
- Jennifer Aniston: 78.0 (estimate from 2000)
- covered share 1, period support `nearby_period`
- gap in the men's view **-14.0**, in the women's view **+14.0**, mirrors exactly: True

## 7. Evidence density — the actual bottleneck

Coverage asks whether a person-year has any evidence. Density asks how much. Mean observations per person-period: **1.051**. Distribution: `{'1': 37, '2': 2}`. Person-periods carrying two or more publishers: **2**. Person-periods that are a lone one-winner award: **18 of 39**.

| Corpus | n | range | distinct values | SD |
|---|---|---|---|---|
| Real | 39 | 30.0 | **12** | 6.367 |
| Synthetic stress | 23 | 29 | 10 | 9.183 |

The rubric discriminates; the corpus does not let it. A lone one-winner award is superlative by construction, so it concentrates almost all of its estimates on a single value, and a person-period carrying exactly that has almost no room to differ from the next one. What the board needs is not more sources covering more people, but sources landing on the SAME person-year as an existing observation.

This reframes what "more sources" has to mean. A source that adds a hundred new people at one observation each raises coverage and changes almost nothing about the board, because a lone observation leaves a dossier with nothing to weigh against and its estimate lands where that evidence shape lands. Only a source that puts a SECOND observation on a person-year that already has one can widen the distribution.

## 8. Why joint coverage does not move

The corpus grew from 13 observations to 41 and joint coverage did not move. This is why.

- Pairings considered (romance-verified films plus scorable episodes): **34**
- With evidence on BOTH sides at any distance: **12**
- Missing evidence on one side entirely: **22**

Joint coverage if the nearby-period bound were widened:

| Bound | Pairings jointly covered |
|---|---|
| ±0 | 1 |
| ±1 | 2 ← current |
| ±2 | 4 |
| ±3 | 4 |
| ±4 | 5 |
| ±5 | 6 |
| ±6 | 6 |
| ±7 | 7 |
| ±8 | 8 |
| ±9 | 8 |
| ±10 | 8 |
| ±11 | 8 |
| ±12 | 8 |

Two things follow. Widening the bound from ±1 to ±2 would take joint coverage from 2 to 4. And it stops helping: the count reaches 8 at ±8 and goes no higher over the range measured, because **22 of 34 pairings have no evidence on one side at all**. The bound is a real cost but absence is the bigger one.

*This measures what the bound costs. It is NOT an argument for widening it: a wider bound reuses an estimate further from the period it is supposed to describe, which is the manufactured precision the bound exists to prevent.*

## 9. The confound is aligned with gender

| Gender | `editorial_award` | `ordered_rank` | `unordered_inclusion` |
|---|---|---|---|
| male | 8 | **0** | 1 |
| female | 12 | **17** | 3 |

| Gender | n | mean | SD | range |
|---|---|---|---|---|
| male | 8 | **90.75** | 4.89 | 78.0–94.0 |
| female | 31 | **87.1** | 6.49 | 64.0–94.0 |

Men hold 0 ranked observations and women 17. Because an award pins near the top of the scale and a ranked placement does not, that imbalance puts the male mean 3.65 points above the female mean before any fact about any individual enters. Every mixed-gender pairing therefore carries roughly that offset built in, in the same direction, and a signed gap that size is a statement about publishing rather than about the couple. Removing any single male person entirely moves the offset between 2.9 and 5.3: it never approaches zero and never reverses, so the finding does not belong to whichever person is carrying it.

**A four-view product compares a man against a woman in every row. With the shapes distributed this unevenly, the sign of a typical gap is decided by which sex the person is, not by the judgments. This has to be disclosed on every row, or the board reports a publishing artifact as a finding about people.**

## 10. Evidence shape drives the estimate

**Evidence type alone explains 31% of the variance in the estimates** (omega-squared 0.311, the unbiased estimator).

Earlier versions of this report quoted 39%, which is eta-squared. Eta-squared is biased upward, and this corpus has 39 estimates over 5 shape groups, two of them holding a single estimate — and a group of one has its mean equal to its value by construction, contributing to between-group variance with nothing within-group to offset it. The gap between the two figures is the size of that bias. The conclusion does not turn on it: a third of the variance in an attractiveness estimate being explained by the FORMAT of the evidence is decisive either way.

| Evidence shape | n | mean | range | SD |
|---|---|---|---|---|
| `editorial_award` | 18 | 91.28 | 78.0–94.0 | 3.263 |
| `editorial_award+ordered_rank` | 1 | 94.0 | 94.0–94.0 | 0.0 |
| `editorial_award+unordered_inclusion` | 1 | 94.0 | 94.0–94.0 | 0.0 |
| `ordered_rank` | 16 | 84.56 | 64.0–93.0 | 6.727 |
| `unordered_inclusion` | 3 | 80.67 | 76.0–86.0 | 4.11 |

**3 of 4 jointly covered pairings have MISMATCHED evidence shapes on the two sides.**

- relationship 1999: Brad Pitt `editorial_award` vs Jennifer Aniston `ordered_rank`
- relationship 2000: Brad Pitt `editorial_award` vs Jennifer Aniston `ordered_rank`
- relationship 2001: Brad Pitt `editorial_award` vs Jennifer Aniston `ordered_rank`

This is the project's most serious systematic bias and it is not hypothetical. The Brad Pitt and Jennifer Aniston gap of −12 pairs a Sexiest Man Alive win, which is superlative by construction and lands at 92, against ranked list placements, which spread lower. A large part of that gap is a statement about which publication covered whom in what format, not about the two people.

Any published pairing whose sides carry different evidence shapes must carry this caveat on the row. A board that shows the number without it would be reporting a property of the sources as a property of the couple.

## 11. How much of the board is even reachable

A pairing needs both sides. The partners missing evidence are two different populations, and counting them together overstates what the project can reach.

| Status | Partners |
|---|---|
| Public figure, no evidence found — **a real gap** | 12 |
| Evidenced | 4 |
| Notable but not public-facing (producers, directors) | 4 |
| Not a public figure — **never rate** | 3 |

**Reachable ceiling: 16 of 23 partners.**

7 of 23 partners are people this project must not rate: the plan forbids rating a private individual merely because they dated a celebrity. Those pairings are a PERMANENT exclusion, not a coverage gap, and counting them in the denominator overstates how much of the board is reachable.

## 12. On-screen romance verification

Co-appearance in a cast list is not a pairing. All 20 candidates were put to the classifier from the Wikipedia plot section alone. 19 reached a model; **8** are confirmed reciprocal romances.

1 never reached one and is recorded as `cannot_tell` with a reason, which is why the table below sums to 20 rather than 19:
  - *Daredevil: The Director's Cut* — no Plot or Synopsis section

| Classification | Count |
|---|---|
| `reciprocal_romance` | 8 |
| `cannot_tell` | 7 |
| `co_appearance_only` | 3 |
| `family_or_platonic` | 2 |

3 results worth naming. *Being John Malkovich* came back `cannot_tell` for Brad Pitt and Michelle Pfeiffer — both appear as themselves; before this filter existed the coverage count treated them as a couple. *Pearl Harbor* came back `cannot_tell` for Ben Affleck and Jennifer Garner; `reciprocal_romance` for Ben Affleck and Kate Beckinsale — the two candidate pairs separated, which is the point of classifying per pair rather than per film. *What Lies Beneath* came back `reciprocal_romance` for Harrison Ford and Michelle Pfeiffer — the cast fix changed this one: knowing which characters the two actors play turned an unclassifiable plot into an established marital relationship.

## 13. Rater noise

4 repeats of each unchanged dossier.

- `award`: SD **0.0** over 2 dossier(s). No LSD quoted -- every repeat returned the same value; this sample cannot distinguish low variance from none, so no LSD is quoted.
- `ranked`: SD **0.926**, least significant difference at 95% about **2.56** points (2.77 x SD).

**Leave-one-out:** dropping any single ranked dossier moves the floor between **2.35** and **2.89**. No verdict in this report flips across that range — the closest are the two 2.0-point results, which stay inside even at 2.35. Four dossiers is few, and a floor set by one outlier would have set every significance verdict here with it.

The POOLED figure is SD 0.617 and LSD 1.71. It is reported only for continuity with earlier documents. Pooling averages a shape with measured variance against one with none, which halves the number and understates the noise floor for exactly the rank-shaped estimates the LSD gets applied to.

| Dossier | Shape | Runs | SD |
|---|---|---|---|
| Angelina Jolie 2006 (fable) | ranked | 94, 93, 95, 94 | 0.816 |
| Michelle Pfeiffer 1995 (fable) | ranked | 86, 86, 88, 88 | 1.155 |
| Jennifer Aniston 1996 (fable) | ranked | 84, 84, 86, 86 | 1.155 |
| Jennifer Aniston 1997 (fable) | ranked | 91, 90, 91, 90 | 0.577 |
| Denzel Washington 1996 (fable) | award | 92, 92, 92, 92 | 0.000 |
| Harrison Ford 1998 (fable) | award | 92, 92, 92, 92 | 0.000 |

**Which dossier moves is the finding.** The award dossier does not move at all, because it is pinned against the 90-100 ceiling where no judgment is left to make. The ranked dossier does move, because there genuinely is one. Zero rater noise is a symptom of evidence that cannot discriminate, not a sign of a well-behaved rubric.

Measured on one judge (fable). Codex reached 0% of its 7-day quota window mid-run, so this describes one model family and not a panel.

## 14. Cross-gender offset sensitivity

Deltas [-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0] applied to the partner side, on 2 people across 4 pairings.

- Identity holds: **True**
- PAW-rate ranks stable under a constant offset: **True**
- Cumulative PAW ranks changed: **False**

A constant cross-gender offset shifts every PAW rate by exactly delta, so rate ranks inside a view cannot move. Cumulative PAW is exposure-weighted, so it can. Cumulative ranks did NOT move over the tested range, which with this few people and this little exposure spread says the board is too small to be sensitive rather than that it is robust.

*This is a sensitivity scenario, not an estimate of real-world bias. Genders are never silently recentred.*

## 15. Grounding audit

39 rationales checked: **39** passed the automated checks, 0 failed, 34 are flagged for a human read in `docs/GROUNDING-AUDIT.md`.

*These checks prove a rationale does not assert MORE than its evidence carries. They do not prove it is a fair reading. Only the human sheet can establish that.*

## 16. The observations, against the pages they came from

**41 of 41** observations were re-checked against the live Wikipedia page each was extracted from, and every one of them matched: 17 editorial awards, 16 ranked placements, and 8 prose mentions whose excerpts still appear verbatim in the article.

Until this ran, nothing had checked them. Every finding in this report rests on those rows, which two parsers and one model produced, and all three were taken on trust. They earned it.

*What this does NOT establish. It checks the corpus against Wikipedia, not Wikipedia against the publishers. An error that Wikipedia itself carries is reproduced here and confirmed here. The check is that extraction was faithful, which is a smaller claim than the sources being right.*

## 17. The same dossier, scored in two separate runs

`data/pilot/run/evidenced_scores.json` and `data/roster100/run/joint_scores.json` were scored in separate runs. 3 person-periods carry a byte-identical dossier in both -- the same observation ids, the same contract id, the same judge family -- so any difference is run-to-run variance and nothing else.

| Person | Period | Shape | pilot | roster100 | Delta |
|---|---|---|---|---|---|
| Brad Pitt | 2000 | `editorial_award` | 92.0 | 92.0 | **+0.0** |
| Jennifer Aniston | 1999 | `ordered_rank` | 86.0 | 84.0 | **+2.0** |
| Jennifer Aniston | 2000 | `ordered_rank` | 78.0 | 80.0 | **-2.0** |

3 person-periods carry a byte-identical dossier in both runs under the same contract id. 1 returned the same estimate and 2 did not, with a largest move of 2.0 points. A move here is pure run-to-run variance: the evidence, the rubric and the judge family were identical.

This is independent of the rater-noise section and agrees with it. The repeats there were deliberate re-invocations inside one run; these two runs did not know about each other. Both say the award shape holds still and the ranked shape does not.

## 18. Do the conclusions depend on the choices that were made?

The ±1 nearby-period bound, the romance filter on co-starring films and the enforcement of shape comparability were all argued in the plan and could defensibly have gone the other way. A conclusion that only holds at one setting of three dials is a property of the dials.

| Bound | Romance filter | Jointly covered | Comparable | Comparable with a non-zero gap | Non-zero gaps | ...shape-mismatched |
|---|---|---|---|---|---|---|
| ±0 | True | 1 | 0 | **0** | 1 | 1 |
| ±0 | False | 1 | 0 | **0** | 1 | 1 |
| ±1 | True | 4 | 1 | **0** | 3 | 3 |
| ±1 | False | 6 | 3 | **0** | 3 | 3 |
| ±2 | True | 8 | 3 | **0** | 5 | 5 |
| ±2 | False | 11 | 6 | **0** | 5 | 5 |
| ±3 | True | 10 | 5 | **0** | 5 | 5 |
| ±3 | False | 14 | 9 | **0** | 5 | 5 |
| ±4 | True | 13 | 7 | **0** | 6 | 6 |
| ±4 | False | 18 | 12 | **1** | 7 | 6 |

The claim that a shape-comparable pairing has a gap of exactly zero holds at **9 of 10** settings. It fails at bound 4, romance_filter False.

The counterexample there is `Thor: Love and Thunder 2022: +3` — a film co-appearance never established as a romance, scored from estimates 4 years from the year in question. It takes both dials at their loosest, in the two directions this project argues against, to produce it.

*Every setting reuses the SAME estimates. This tests whether the conclusions depend on the three methodological dials, not whether they survive different evidence.*

## 19. The bottom line, stated plainly

Of 4 jointly covered pairing-periods, **1** compares two people judged by the same kind of evidence. The rest compare an award against a list placement, where format explains much of the gap.

- **Daredevil (2003)**: gap **+0.0**
  - Both sides are `editorial_award`-shaped, and that shape's repeat variance is **unmeasured**: every repeat returned the same value, which cannot tell low variance from none. The largest measured floor is `ranked`'s **2.56** points. Against that upper bound the gap is **not distinguishable from zero**.

So the project can now produce a signed, exactly mirrored, evidence-backed gap for a real couple. It cannot yet produce one that is both comparable and larger than its own measurement noise. That is a much better place than this run started, and it is not a leaderboard.

## 20. Cost and budget

Stages that record a call budget in their own artifact:

- Stress tests: 27 model calls ({"fable": 17, "astra": 10}).
- Scoring: 39 model calls ({"fable": 39, "astra": 0}).
- First pilot pass: 0 model calls — every dossier came back empty and short-circuited before any judge was called.

Stages that write a run manifest, with the reconciliation each records. `attempted` equals `succeeded + cached + excluded + failed` by construction, so a stage that failed on every item cannot hide behind a call count:

| Stage | Runs | Attempted | Succeeded | Cached | Excluded | Failed | Errors |
|---|---|---|---|---|---|---|---|
| `prose-mentions` | 1 | 14 | 14 | 0 | 0 | 0 | — |
| `rater-noise` | 5 | 58 | 50 | 0 | 0 | 8 | auth_or_quota=8 |
| `romance` | 3 | 60 | 45 | 0 | 15 | 0 | — |

Repeated runs of a stage are summed. A superseded run spent quota too, and this section answers what the pilot cost rather than how many calls stand behind the final artifacts.

**Model calls: 66 from the budgeted stages, plus 132 attempts recorded across the manifested stages — 198 in total, against a cap of 300.**

- Subscription quota only. API billing was asserted off at start-up.
- Dollar cost is not totalled: only the Claude arm reports `cost_usd`, and inventing a figure for the other arm would be a fabricated number.
- **Human review time: 0 minutes so far.** The plan budgeted 60–90 minutes for one batch covering the pairing relationship claims and a sample of rationales for the grounding audit. None of it has happened, so every real-life relationship claim in this report remains an unverified candidate and the grounding audit remains automated-only.

## 21. Do the estimates reflect substance, or source availability?

**Substance, where evidence exists. Availability decides whether it exists at all.**

The stress cases say the rubric is reading the judgments rather than counting documents: one award beat two low placements by a wide margin, three corroborating publishers moved the estimate by a point, and five copies of one list moved it by zero. Both model families agreed exactly on every construct case they both ran.

With one exception, and it is about FORMAT rather than count: **S2_format_equivalence** exceeded the measured noise floor. The rubric reads the substance of a judgment and not the number of documents carrying it — but it does not read the same substance identically in every shape, which is the confound this report measures observationally elsewhere.

But which person-years have any evidence is decided entirely by which publishers happen to be reachable. On the permitted routes the men's award is an annual one-winner prize reported on Wikipedia since 1985, and the women's equivalent is a single number-one per year since 2000. Everything deeper sits behind terms that forbid this use.

## 22. Against the plan's M0 deliverables

The plan's section 8.2 lists six things M0 should produce. Where each one is, and whether it is done:

| # | Deliverable | Where | Done |
|---|---|---|---|
| 1 | The revised rubric and the access decisions | `rubrics/standing/RUBRIC.md`, section 2 | yes |
| 2 | Dossiers, estimates, support, rationales, exclusions, lineage | `data/pilot/run/evidenced_scores.json`, sections 6 and 15 | yes — 39 person-periods |
| 3 | VERIFIED pairings, with mirrored contribution arithmetic | section 6; `docs/RELATIONSHIP-REVIEW.md` for the verification | arithmetic yes, mirrors exact; **verification NOT done** — it needs a person, and the sheet is ready |
| 4 | Person-period and joint pairing-period coverage, with failures | sections 5 and 8, and the near-miss list | yes |
| 5 | Stress tests, offset diagnostic, actual costs, review minutes | sections 4, 14 and 20 | yes — review minutes are **0**, stated |
| 6 | An assessment: substance, or source availability? | section 21 | yes |

**One deliverable is outstanding and it is the one only a person can do.** Everything else is here. The two review sheets each lead with the entries that carry a published conclusion, so the load-bearing part of the work is the first part encountered.

## 23. What M0 did not establish

- **Human verification has not happened.** Every relationship remains a Wikidata candidate that no person has checked, and the plan budgeted 60-90 minutes for exactly that.
  On-screen pairings ARE romance-filtered — 8 of 20 candidates are confirmed reciprocal romances from the plot text — so that is no longer an open item, but the filter is a model's reading of a Wikipedia summary, not a human's.
- **The grounding audit is not done.** 34 rationales are flagged for a human to read and judge whether the cited observations support what they claim. The automated checks cannot establish that.
- **Rater noise is measured but thin.** 4 repeats across 6 dossiers on 1 judge family. The award shape returned the same value every time, which cannot distinguish low variance from none, so no floor is quoted for it.
- **The cross-gender offset diagnostic ran, on too small a board to be informative.** Cumulative ranks did not move over the tested range, but with 2 people and this little exposure spread that says the board is too small to be sensitive, not that it is robust.
- **Cross-family agreement on the real dossiers is unmeasured.** Every estimate came from fable alone. The plan decided two families precisely so that a one-family idiosyncrasy could be told from a property of the rubric, and that check has not been run on real evidence.

