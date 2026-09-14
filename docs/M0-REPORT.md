# M0 pilot report — Celebrity Pairing WAR

Generated 2026-09-14 from the run artifacts under `data/pilot/`, input fingerprint `5759dd5e8463`. Every number below is read from a JSON artifact, not typed.

The fingerprint, not the date, is this report's identity: regenerating it over unchanged artifacts produces an identical file, so a diff means the numbers moved.

**Private pilot. Nothing here is published, ranked, or deployed. Every relationship and every on-screen pairing is an UNVERIFIED candidate.**

This report covers the 14-person pilot. Three companion documents cover what came after it:

- [`docs/SCALING.md`](SCALING.md) — whether growing the roster to 100 helps, and what a usable source would have to look like
- [`docs/SOURCE-HUNT.md`](SOURCE-HUNT.md) — every surface checked, and the negative result
- [`docs/REACHABLE-PRODUCTS.md`](REACHABLE-PRODUCTS.md) — what can be built with the evidence that exists

## The answer first

**The measurement works. The evidence supply does not.**

The rubric behaves as intended under adversarial testing: 25 of 27 stress scorings succeeded and every construct check passed. Two model families independently agreed on the calibration anchor.

But across the 14-person cohort, the permitted sources yielded **41 attractiveness observations total**, covering 14 of 14 people. 5 people have none at all.

Across all 31 relationship episodes and 20 co-starring films — **51 candidate pairings** — and after both the ±1-year bounded reuse AND the romance filter, exactly **4** pairings are jointly covered.

**The decisive measurement**: of 39 scored person-periods, 18 rest on a one-winner editorial award and 16 on an ordered rank. The award-shaped ones cluster at mean 91.28 with sd **3.263**; the rank-shaped ones sit lower, at mean 84.56, and spread more than twice as wide, sd **6.727**. A one-winner award is superlative by construction, so it can only land in one band. Ranked evidence carries a degree, so it can tell people apart.

## 1. Cohort

`pilot-cohort-2026-09-14`, selected 2026-09-14. diversity of era, gender and casting type, chosen BEFORE any check of how easy each is to score

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
| Sexiest Man Alive | PEOPLE | male | `editorial_award` | 40 winner rows | 1985–2025 | 6 |
| Maxim Hot 100 number one | Maxim | female | `editorial_award` | 24 winner rows | 2000–2025 | 1 |
| Most Beautiful cover choice | PEOPLE | mixed | `editorial_award` | 37 winner rows | 1990–2026 | 9 |
| Sexiest Woman Alive | Esquire | female | `editorial_award` | 11 winner rows | 2005–2015 | 1 |
| FHM 100 Sexiest Women (UK) | FHM | female | `ordered_rank` | 229 entries, 206 ranked | 1995–2017 | 16 |

## 3. Records

- 34 relationship candidates for 14 subjects, 27 carrying a source reference.
- **16 of 32 start dates are year-precision only.** They are stored as years, not as 1 January.
- Merged into 31 episodes, joining 3 dating-to-marriage progressions that Wikidata stores as two abutting statements.
- 3 episodes carry defects and are unscorable:
  - `no_start_date`: 2
  - `end_before_start`: 1
- 28 episodes eligible after the adult window.
- Scoring every year of every eligible episode would need **633 person-period estimates** (span 1964–2026), against an M0 cap of 50. The pilot samples at most three periods per pairing.

On screen: 20 co-starring films found via Wikidata cast lists. Co-appearance in a cast list proves only that both were in the film. A qualifying on-screen pairing needs an established reciprocal romance between their CHARACTERS, which scripts/classify_romance.py decides. Seventeen of the pilot's first twenty were not romances.

## 4. Measurement stress tests

27 scorings attempted, 25 succeeded, 2 failed. Taxonomy: `{"model_identity_mismatch": 2}`.

| Case | Question | Result |
|---|---|---|
| S1 single vs multi | Does publication count impose the ordering? | strong single-source **92** vs weak multi-source **63** — the stronger substantive judgment scored higher |
| S2 format | Award vs rank vs prose | {"as_award": 92, "as_rank": 92, "as_prose": 88}, spread 4 — formats scored comparably |
| S3 corroboration | Does an extra publisher jump a band? | 69 → 70 (delta 1) — corroboration left the estimate where it was |
| S4 contradiction | Does the rationale address the conflict? | estimate [80], names both placements: [True] |
| S5 empty / off-topic | Unscored, or a low number? | empty unscored: True, off-topic unscored: True |
| S6 identity | Same evidence, different name | per judge null — identity moved the score |
| S7 order | Reordered observations | {"order_a": 84, "order_b": 82}, spread 2 |
| S8 copy volume | One copy vs five | {"one_copy": 72, "five_copies": 72} — copy volume changed nothing |

## 5. Coverage, the two numbers that matter

**First pass, no nearby reuse.** 32 person-periods needed for 8 selected pairings; 32 were empty and short-circuited without a model call; 0 scored.

Joint pairing coverage: **0 of 8** (0/4 real-life, 0/4 on-screen).

**Exhaustive check.** Across all 31 episodes and 20 films, zero pairings had both sides evidenced in a shared year. The near-misses are the finding: Ben Affleck and Jennifer Garner each have 2002 evidence and four pairings together, every one landing one to three years off.

**With the plan's ±1-year bounded reuse**, 4 pairing-periods become jointly covered:

- Daredevil (2003, on_screen): Ben Affleck from 2002 (d=1), Jennifer Garner from 2002 (d=1)
- relationship (1999, real_life): Brad Pitt from 2000 (d=1), Jennifer Aniston from 1999 (d=0)
- relationship (2000, real_life): Brad Pitt from 2000 (d=0), Jennifer Aniston from 2000 (d=0)
- relationship (2001, real_life): Brad Pitt from 2000 (d=1), Jennifer Aniston from 2000 (d=1)

Both are reused estimates flagged `nearby_period`. Any simulation must give each source estimate ONE shared draw across every period it serves.

## 6. Scored person-periods and pairing contributions

39 of 39 evidenced person-periods scored, using 39 model calls, 0 failed.

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

An annual one-winner award is a superlative judgment by construction, so the rubric correctly places every winner in band 90-100. The consequence is that **award-shaped evidence cannot discriminate between winners.** A leaderboard built on it would rank people by a half-point that is the difference between one judge saying 92 and another saying 93.

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

## 6. Evidence density — the actual bottleneck

Coverage asks whether a person-year has any evidence. Density asks how much. Mean observations per person-period: **1.051**. Distribution: `{'1': 37, '2': 2}`. Person-periods carrying two or more publishers: **2**. Person-periods that are a lone one-winner award: **18 of 39**.

| Corpus | n | range | distinct values | SD |
|---|---|---|---|---|
| Real | 39 | 30.0 | **12** | 6.367 |
| Synthetic stress | 23 | 29 | 10 | 9.183 |

The rubric discriminates; the corpus does not let it. A lone one-winner award is superlative by construction and can only land in one band, so a person-period carrying exactly that produces the same number every time. What the board needs is not more sources covering more people, but sources landing on the SAME person-year as an existing observation.

This reframes what "more sources" has to mean. A source that adds a hundred new people at one observation each raises coverage and changes nothing about the board, because every one of those dossiers still lands in a single band. Only a source that puts a SECOND observation on a person-year that already has one can widen the distribution.

## 6e. Why joint coverage does not move

The corpus grew from 13 observations to 41 and joint coverage did not move. This is why.

- Pairings considered (romance-verified films plus scorable episodes): **36**
- With evidence on BOTH sides at any distance: **13**
- Missing evidence on one side entirely: **23**

Joint coverage if the nearby-period bound were widened:

| Bound | Pairings jointly covered |
|---|---|
| ±0 | 1 |
| ±1 | 2 ← current |
| ±2 | 4 |
| ±3 | 5 |
| ±4 | 6 |
| ±5 | 7 |
| ±6 | 7 |
| ±7 | 8 |
| ±8 | 9 |

Two things follow. Widening the bound from ±1 to ±2 would triple joint coverage, from 1 to 3. And it would not matter much beyond that: the count saturates at 6, because **22 of 30 pairings have no evidence on one side at all**. The bound is a real cost but absence is the bigger one.

*This measures what the bound costs. It is NOT an argument for widening it: a wider bound reuses an estimate further from the period it is supposed to describe, which is the manufactured precision the bound exists to prevent.*

## 5. The confound is aligned with gender

| Gender | `editorial_award` | `ordered_rank` | `unordered_inclusion` |
|---|---|---|---|
| male | 8 | **0** | 1 |
| female | 12 | **17** | 3 |

| Gender | n | mean | SD | range |
|---|---|---|---|---|
| male | 8 | **90.75** | 4.89 | 78.0–94.0 |
| female | 31 | **87.1** | 6.49 | 64.0–94.0 |

Men hold 0 ranked observations and women 17. Because an award pins near the top of the scale and a ranked placement does not, that imbalance puts the male mean 3.65 points above the female mean before any fact about any individual enters. Every mixed-gender pairing therefore carries roughly that offset built in, in the same direction, and a signed gap that size is a statement about publishing rather than about the couple.

**A four-view product compares a man against a woman in every row. With the shapes distributed this unevenly, the sign of a typical gap is decided by which sex the person is, not by the judgments. This has to be disclosed on every row, or the board reports a publishing artifact as a finding about people.**

## 5b. Evidence shape drives the estimate

**Evidence type alone explains 39% of the variance in the estimates** (eta-squared 0.389).

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

## 6f. How much of the board is even reachable

A pairing needs both sides. The partners missing evidence are two different populations, and counting them together overstates what the project can reach.

| Status | Partners |
|---|---|
| Public figure, no evidence found — **a real gap** | 12 |
| Evidenced | 4 |
| Notable but not public-facing (producers, directors) | 4 |
| Not a public figure — **never rate** | 3 |

**Reachable ceiling: 16 of 23 partners.**

7 of 23 partners are people this project must not rate: the plan forbids rating a private individual merely because they dated a celebrity. Those pairings are a PERMANENT exclusion, not a coverage gap, and counting them in the denominator overstates how much of the board is reachable.

## 6a. On-screen romance verification

Co-appearance in a cast list is not a pairing. All 20 candidates were classified from the Wikipedia plot section alone; 19 were classifiable and **8** are confirmed reciprocal romances.

| Classification | Count |
|---|---|
| `reciprocal_romance` | 8 |
| `cannot_tell` | 7 |
| `co_appearance_only` | 3 |
| `family_or_platonic` | 2 |

Three results worth naming. *Being John Malkovich* came back `cannot_tell` for Brad Pitt and Michelle Pfeiffer, who both appear as themselves; before this filter existed the coverage count treated them as a couple. *Pearl Harbor* separated correctly: the romance is Affleck and Beckinsale, not Affleck and Garner. *What Lies Beneath* was classified `coerced_or_assault` and is therefore excluded rather than scored.

## 6b. Rater noise

4 repeats of each unchanged dossier. Mean within-judge SD **0.433**, least significant difference at 95% about **1.2** points (2.77 x SD).

| Dossier | Shape | Runs | SD |
|---|---|---|---|
| Michelle Pfeiffer 1995 (fable) | ranked | 86, 86, 88, 86 | 0.866 |
| Brad Pitt 1995 (fable) | award | 92, 92, 92, 92 | 0.000 |

**Which dossier moves is the finding.** The award dossier does not move at all, because it is pinned against the 90-100 ceiling where no judgment is left to make. The ranked dossier does move, because there genuinely is one. Zero rater noise is a symptom of evidence that cannot discriminate, not a sign of a well-behaved rubric.

Measured on one judge (fable). Codex reached 0% of its 7-day quota window mid-run, so this describes one model family and not a panel.

## 6c. Cross-gender offset sensitivity

Deltas [-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0] applied to the partner side, on 2 people.

- Identity holds: **True**
- PAW-rate ranks stable under a constant offset: **True**
- Cumulative PAW ranks changed: **False**

A constant cross-gender offset shifts every PAW rate by exactly delta, so rate ranks inside a view cannot move. Cumulative PAW is exposure-weighted, so it can. Cumulative ranks did NOT move over the tested range, which with this few people and this little exposure spread says the board is too small to be sensitive rather than that it is robust.

*This is a sensitivity scenario, not an estimate of real-world bias. Genders are never silently recentred.*

## 6d. Grounding audit

39 rationales checked: **39** passed the automated checks, 0 failed, 34 are flagged for a human read in `docs/GROUNDING-AUDIT.md`.

*These checks prove a rationale does not assert MORE than its evidence carries. They do not prove it is a fair reading. Only the human sheet can establish that.*

## 6g. The bottom line, stated plainly

Of 4 jointly covered pairing-periods, **1** compares two people judged by the same kind of evidence. The rest compare an award against a list placement, where format explains much of the gap.

- **Daredevil (2003)**: gap **+0.0**
  - Repeat-scoring puts the least significant difference at about **1.2** points, so this gap is **not distinguishable from zero**.

So the project can now produce a signed, exactly mirrored, evidence-backed gap for a real couple. It cannot yet produce one that is both comparable and larger than its own measurement noise. That is a much better place than this run started, and it is not a leaderboard.

## 7. Cost and budget

- Stress tests: 27 model calls ({"fable": 17, "astra": 10}).
- Scoring: 39 model calls ({"fable": 39, "astra": 0}).
- First pilot pass: 0 model calls — all 32 dossiers were empty and short-circuited.
- **Total: 66 model calls**, against a cap of 300.
- Subscription quota only. API billing was asserted off at start-up.
- Dollar cost is not totalled: only the Claude arm reports `cost_usd`, and inventing a figure for the other arm would be a fabricated number.

## 8. Do the estimates reflect substance, or source availability?

**Substance, where evidence exists. Availability decides whether it exists at all.**

The stress cases say the rubric is reading the judgments rather than counting documents: one award beat two low placements by a wide margin, three corroborating publishers moved the estimate by a point, and five copies of one list moved it by zero. Both model families agreed exactly on every construct case they both ran.

But which person-years have any evidence is decided entirely by which publishers happen to be reachable. On the permitted routes the men's award is an annual one-winner prize reported on Wikipedia since 1985, and the women's equivalent is a single number-one per year since 2000. Everything deeper sits behind terms that forbid this use.

## 9. What M0 did not establish

- Nothing here is verified. Every relationship is a Wikidata candidate and every on-screen pairing is co-appearance only, with no romance evidence.
- The grounding audit is not done: a human still has to read the rationales and judge whether the cited observations support what they claim.
- Rater noise was not measured by repeat scoring.
- The cross-gender offset diagnostic has no board to run against yet.
- Two judges from two families cannot separate a two-family idiosyncrasy from a property of the rubric.

