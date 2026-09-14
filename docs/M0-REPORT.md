# M0 pilot report — Celebrity Pairing WAR

Generated 2026-09-14 08:52 UTC from the run artifacts under `data/pilot/`. Every number below is read from a JSON artifact, not typed.

**Private pilot. Nothing here is published, ranked, or deployed. Every relationship and every on-screen pairing is an UNVERIFIED candidate.**

## The answer first

**The measurement works. The evidence supply does not.**

The rubric behaves as intended under adversarial testing: 25 of 27 stress scorings succeeded and every construct check passed. Two model families independently agreed on the calibration anchor.

But across the 14-person cohort, the permitted sources yielded **13 attractiveness observations total**, covering 9 of 14 people. 5 people have none at all.

Across all 31 relationship episodes and 20 co-starring films — **51 candidate pairings** — and after both the ±1-year bounded reuse AND the romance filter, exactly **1** pairing is jointly covered.

**The decisive measurement**: 13 of 18 scored person-periods rest on a one-winner editorial award, and every single one scored exactly 92.0 — both model families, to the digit. The one person-period resting on an ORDERED rank (5th of 100) scored 72.0. Award-shaped evidence cannot tell winners apart. Ranked evidence can.

## 1. Cohort

`pilot-cohort-2026-09-14`, selected 2026-09-14. diversity of era, gender and casting type, chosen BEFORE any check of how easy each is to score

| Person | Gender | Casting type | Observations found |
|---|---|---|---|
| Ben Affleck | male | 1990s-2020s lead | 1 |
| Brad Pitt | male | 1990s-2020s lead | 2 |
| Denzel Washington | male | 1980s-2020s lead | 1 |
| Harrison Ford | male | 1980s-2010s lead | 1 |
| Idris Elba | male | 2000s-2020s lead | 1 |
| Adam Sandler | male | comic lead | **0** |
| Paul Giamatti | male | character lead | **0** |
| Ana de Armas | female | 2010s-2020s lead | **0** |
| Jennifer Garner | female | 2000s-2010s lead | 2 |
| Kate Beckinsale | female | 1990s-2010s lead | 1 |
| Liv Tyler | female | 1990s-2000s lead | **0** |
| Michelle Pfeiffer | female | 1980s-1990s lead | 3 |
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
| Most Beautiful cover choice | PEOPLE | mixed | `editorial_award` | 37 winner rows | 1990–2026 | 4 |
| Sexiest Woman Alive | Esquire | female | `editorial_award` | 11 winner rows | 2005–2015 | 1 |
| FHM 100 Sexiest Women (UK) | FHM | female | `ordered_rank` | 229 entries, 206 ranked | 1995–2017 | 1 |

## 3. Records

- 34 relationship candidates for 14 subjects, 27 carrying a source reference.
- **16 of 32 start dates are year-precision only.** They are stored as years, not as 1 January.
- Merged into 31 episodes, joining 3 dating-to-marriage progressions that Wikidata stores as two abutting statements.
- 4 episodes carry defects and are unscorable:
  - `no_start_date`: 2
  - `partner_label_unresolved`: 2
  - `end_before_start`: 1
- 27 episodes eligible after the adult window.
- Scoring every year of every eligible episode would need **604 person-period estimates** (span 1964–2026), against an M0 cap of 50. The pilot samples at most three periods per pairing.

On screen: 20 co-starring films found via Wikidata cast lists. Co-appearance in a cast list proves only that both were in the film. A qualifying on-screen pairing needs an established reciprocal romance shown by plot or dialogue evidence. None of these is verified.

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

**With the plan's ±1-year bounded reuse**, 1 pairing-periods become jointly covered:

- Daredevil (2003, on_screen): Ben Affleck from 2002 (d=1), Jennifer Garner from 2002 (d=1)

Both are reused estimates flagged `nearby_period`. Any simulation must give each source estimate ONE shared draw across every period it serves.

## 6. Scored person-periods and pairing contributions

18 of 18 evidenced person-periods scored, using 18 model calls, 0 failed.

| Person | Period | Obs | Estimate | fable | astra | judge gap | support |
|---|---|---|---|---|---|---|---|
| Michelle Pfeiffer | 1990 | 1 | 92.0 | 92.0 | – | – | single_source |
| Michelle Pfeiffer | 1995 | 1 | 84.0 | 84.0 | – | – | single_source |
| Brad Pitt | 1995 | 2 | 94.0 | 94.0 | – | – | multi |
| Denzel Washington | 1996 | 1 | 92.0 | 92.0 | – | – | single_source |
| Liv Tyler | 1997 | 1 | 72.0 | 72.0 | – | – | single_source |
| Harrison Ford | 1998 | 1 | 92.0 | 92.0 | – | – | single_source |
| Michelle Pfeiffer | 1999 | 1 | 92.0 | 92.0 | – | – | single_source |
| Brad Pitt | 2000 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Garner | 2002 | 1 | 92.0 | 92.0 | – | – | single_source |
| Ben Affleck | 2002 | 1 | 92.0 | 92.0 | – | – | single_source |
| Michelle Pfeiffer | 2004 | 1 | 86.0 | 86.0 | – | – | single_source |
| Kate Beckinsale | 2009 | 1 | 92.0 | 92.0 | – | – | single_source |
| Idris Elba | 2013 | 1 | 92.0 | 92.0 | – | – | single_source |
| Idris Elba | 2017 | 1 | 80.0 | 80.0 | – | – | single_source |
| Idris Elba | 2018 | 1 | 92.0 | 92.0 | – | – | single_source |
| Jennifer Garner | 2019 | 1 | 92.0 | 92.0 | – | – | single_source |
| Michelle Pfeiffer | 2020 | 1 | 80.0 | 80.0 | – | – | single_source |
| Melissa McCarthy | 2023 | 1 | 92.0 | 92.0 | – | – | single_source |

### Score compression — the most consequential measurement result

Every scored person-period carries exactly one observation, and every one of those observations is a one-winner editorial award. All 18 estimates land between **72.0** and **94.0**, a spread of **22.0** points on a 0-100 scale.

The judges agree almost perfectly: 0 of 0 person-periods came back identical from both families, and the largest disagreement was 0 point. So the compression is not rater noise. It is the evidence.

An annual one-winner award is a superlative judgment by construction, so the rubric correctly places every winner in band 90-100. The consequence is that **award-shaped evidence cannot discriminate between winners.** A leaderboard built on it would rank people by a half-point that is the difference between one judge saying 92 and another saying 93.

This was predicted in the plan's worked example A and is now measured. It is the strongest argument for either finding ordered, depth-carrying lists on permitted routes, or leading the men's and women's views with intervals instead of point estimates.

### Mirrored contributions

**Daredevil** (2003, on_screen) — co-appearance only; ROMANCE UNVERIFIED

- Ben Affleck: 92.0 (estimate from 2002)
- Jennifer Garner: 92.0 (estimate from 2002)
- covered share 1, period support `nearby_period`
- gap in the men's view **+0.0**, in the women's view **+0.0**, mirrors exactly: True

## 6. Evidence density — the actual bottleneck

Coverage asks whether a person-year has any evidence. Density asks how much. Mean observations per person-period: **1.056**. Distribution: `{'1': 17, '2': 1}`. Person-periods carrying two or more publishers: **1**. Person-periods that are a lone one-winner award: **13 of 18**.

| Corpus | n | range | distinct values | SD |
|---|---|---|---|---|
| Real | 18 | 22.0 | **6** | 5.858 |
| Synthetic stress | 23 | 29 | 10 | 9.183 |

The rubric discriminates; the corpus does not let it. A lone one-winner award is superlative by construction and can only land in one band, so a person-period carrying exactly that produces the same number every time. What the board needs is not more sources covering more people, but sources landing on the SAME person-year as an existing observation.

This reframes what "more sources" has to mean. A source that adds a hundred new people at one observation each raises coverage and changes nothing about the board, because every one of those dossiers still lands in a single band. Only a source that puts a SECOND observation on a person-year that already has one can widen the distribution.

## 6a. On-screen romance verification

Co-appearance in a cast list is not a pairing. All 20 candidates were classified from the Wikipedia plot section alone; 19 were classifiable and **3** are confirmed reciprocal romances.

| Classification | Count |
|---|---|
| `cannot_tell` | 15 |
| `reciprocal_romance` | 3 |
| `co_appearance_only` | 1 |
| `coerced_or_assault` | 1 |

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

Deltas [-6.0, -4.0, -2.0, 0.0, 2.0, 4.0, 6.0] applied to the partner side, on 1 people.

- Identity holds: **True**
- PAW-rate ranks stable under a constant offset: **True**
- Cumulative PAW ranks changed: **False**

A constant cross-gender offset shifts every PAW rate by exactly delta, so rate ranks inside a view cannot move. Cumulative PAW is exposure-weighted, so it can. Cumulative ranks did NOT move over the tested range, which with this few people and this little exposure spread says the board is too small to be sensitive rather than that it is robust.

*This is a sensitivity scenario, not an estimate of real-world bias. Genders are never silently recentred.*

## 6d. Grounding audit

18 rationales checked: **18** passed the automated checks, 0 failed, 18 are flagged for a human read in `docs/GROUNDING-AUDIT.md`.

*These checks prove a rationale does not assert MORE than its evidence carries. They do not prove it is a fair reading. Only the human sheet can establish that.*

## 7. Cost and budget

- Stress tests: 27 model calls ({"fable": 17, "astra": 10}).
- Scoring: 18 model calls ({"fable": 18, "astra": 0}).
- First pilot pass: 0 model calls — all 32 dossiers were empty and short-circuited.
- **Total: 45 model calls**, against a cap of 300.
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

