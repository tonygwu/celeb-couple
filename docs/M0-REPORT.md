# M0 pilot report — Celebrity Pairing WAR

Generated 2026-09-14 08:11 UTC from the run artifacts under `data/pilot/`. Every number below is read from a JSON artifact, not typed.

**Private pilot. Nothing here is published, ranked, or deployed. Every relationship and every on-screen pairing is an UNVERIFIED candidate.**

## The answer first

**The measurement works. The evidence supply does not.**

The rubric behaves as intended under adversarial testing: 25 of 27 stress scorings succeeded and every construct check passed. Two model families independently agreed on the calibration anchor.

But across the 14-person cohort, the permitted sources yielded **7 attractiveness observations total**, covering 6 of 14 people. 8 people have none at all.

Across all 31 relationship episodes and 20 co-starring films — **51 candidate pairings** — exactly **zero** had both people evidenced in the same year. Applying the plan's ±1-year bounded reuse raises that to **2**.

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
| Jennifer Garner | female | 2000s-2010s lead | 1 |
| Kate Beckinsale | female | 1990s-2010s lead | **0** |
| Liv Tyler | female | 1990s-2000s lead | **0** |
| Michelle Pfeiffer | female | 1980s-1990s lead | **0** |
| Melissa McCarthy | female | comic lead | **0** |
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

- **Sexiest Man Alive** (PEOPLE, serves male): 40 winner rows parsed, 1985–2025, 6 matched the cohort.
- **Maxim Hot 100 number one** (Maxim, serves female): 24 winner rows parsed, 2000–2025, 1 matched the cohort.

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

**With the plan's ±1-year bounded reuse**, 2 pairing-periods become jointly covered:

- Pearl Harbor (2001, on_screen): Ben Affleck from 2002 (d=1), Jennifer Garner from 2002 (d=1)
- Daredevil (2003, on_screen): Ben Affleck from 2002 (d=1), Jennifer Garner from 2002 (d=1)

Both are reused estimates flagged `nearby_period`. Any simulation must give each source estimate ONE shared draw across every period it serves.

## 6. Scored person-periods and pairing contributions

7 of 7 evidenced person-periods scored, using 14 model calls, 0 failed.

| Person | Period | Obs | Estimate | fable | astra | judge gap | support |
|---|---|---|---|---|---|---|---|
| Brad Pitt | 1995 | 1 | 92.0 | 92.0 | 92.0 | 0.0 | single_source |
| Denzel Washington | 1996 | 1 | 92.0 | 92.0 | 92.0 | 0.0 | single_source |
| Harrison Ford | 1998 | 1 | 92.0 | 92.0 | 92.0 | 0.0 | single_source |
| Brad Pitt | 2000 | 1 | 92.0 | 92.0 | 92.0 | 0.0 | single_source |
| Jennifer Garner | 2002 | 1 | 92.5 | 93.0 | 92.0 | 1.0 | single_source |
| Ben Affleck | 2002 | 1 | 92.0 | 92.0 | 92.0 | 0.0 | single_source |
| Idris Elba | 2018 | 1 | 92.0 | 92.0 | 92.0 | 0.0 | single_source |

### Score compression — the most consequential measurement result

Every scored person-period carries exactly one observation, and every one of those observations is a one-winner editorial award. All 7 estimates land between **92.0** and **92.5**, a spread of **0.5** points on a 0-100 scale.

The judges agree almost perfectly: 6 of 7 person-periods came back identical from both families, and the largest disagreement was 1.0 point. So the compression is not rater noise. It is the evidence.

An annual one-winner award is a superlative judgment by construction, so the rubric correctly places every winner in band 90-100. The consequence is that **award-shaped evidence cannot discriminate between winners.** A leaderboard built on it would rank people by a half-point that is the difference between one judge saying 92 and another saying 93.

This was predicted in the plan's worked example A and is now measured. It is the strongest argument for either finding ordered, depth-carrying lists on permitted routes, or leading the men's and women's views with intervals instead of point estimates.

### Mirrored contributions

**Pearl Harbor** (2001, on_screen) — co-appearance only; ROMANCE UNVERIFIED

- Ben Affleck: 92.0 (estimate from 2002)
- Jennifer Garner: 92.5 (estimate from 2002)
- covered share 1, period support `nearby_period`
- gap in the men's view **+0.5**, in the women's view **-0.5**, mirrors exactly: True

**Daredevil** (2003, on_screen) — co-appearance only; ROMANCE UNVERIFIED

- Ben Affleck: 92.0 (estimate from 2002)
- Jennifer Garner: 92.5 (estimate from 2002)
- covered share 1, period support `nearby_period`
- gap in the men's view **+0.5**, in the women's view **-0.5**, mirrors exactly: True

## 7. Cost and budget

- Stress tests: 27 model calls ({"fable": 17, "astra": 10}).
- Scoring: 14 model calls ({"fable": 7, "astra": 7}).
- First pilot pass: 0 model calls — all 32 dossiers were empty and short-circuited.
- **Total: 41 model calls**, against a cap of 300.
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

