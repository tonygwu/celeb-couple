# Backlog

Filed by the overnight run of 2026-09-14. Difficulty tags are estimates.

See also `docs/BACKLOG-roster.md` for roster scope and the evidence-source hunt.

~~**Three items below are waiting on a single rubric/schema version bump.**~~
**All three landed together on 2026-09-14**, with the operator's approval to
spend the re-score they cost: `estimate.schema.json`'s nullable enums, the
`contract_id` boundary ambiguity, and the `MENTIONS.md` example that
contradicts rule 3. `standing-rubric-2.0` became `2.1`, `mentions-1.0` became
`1.1`, and the hash scheme became `v2-length-prefixed`, which moved every
contract id including romance's, whose bytes never changed. The procedure they
followed is in [`docs/CONTRACT-BUMP.md`](CONTRACT-BUMP.md); what the re-score
moved is in [`docs/CORRECTIONS.md`](CORRECTIONS.md).

## The defect class this codebase keeps producing

Filed 2026-09-14 after a systematic read of every module. Seven of the night's
findings were the same shape, and naming it is more useful than listing them:

> **A fix that DEGRADES to the behaviour it replaced, silently.**

The fix works. Then its input is unavailable, and instead of refusing it falls
back — to an empty value, a default, a guess — and that fallback is exactly the
broken state the fix was written to eliminate. The system then looks like it is
working on worse data rather than failing on a fixable error, which is the
hardest kind of problem to diagnose because nothing is red.

Instances found, all now refusing or reporting:

| Fix | Fallback | What it restored |
|---|---|---|
| `fetch_cast` (so plots naming CHARACTERS match ACTOR names) | `except: cast = {}` | the 15-of-20 `cannot_tell` rate |
| `title_for_qid` (resolve the article by Wikidata sitelink) | `or c["title"]` | fetching by title; 13 of 20 wrong articles |
| prose-mention merge (density 2 → 12 distinct values) | re-running the fetch alone | a corpus 8 observations thinner |
| per-shape LSD | pooling shapes | a noise floor half its real size |
| `EstimateSpec` per estimate | missing spec → unperturbed value | a zero-width interval reading as certainty |
| manifest reconciliation | temp file created before the check | a zero-byte file as the only alarm |
| label lookup | `except: continue` | "no label" indistinguishable from "network died" |

**The rule that catches them:** when an input a fix depends on is missing, the
fix must REFUSE or RECORD, never substitute. A substituted value is a guess
wearing the shape of a measurement. Every one of these was invisible in the
artifacts until something else failed nearby.

Two of them were caught only because a guard built earlier the same night
fired on a downstream number. Neither would have surfaced on its own.

## Correctness and method

- ~~Deep Water miss in the romance classifier.~~ **Fixed 2026-09-14.** Root
  cause was mine, not the model's: Wikipedia plot summaries describe CHARACTERS
  and never name actors, and the prompt supplied two ACTOR names. Every one of
  the fifteen `cannot_tell` reasons said so explicitly. The classifier now
  fetches the article's Cast section and tells the judge which characters the
  two actors play. `cannot_tell` fell 15 to 7, verified romances rose 3 to 8,
  and Deep Water classifies correctly. Joint coverage did not move, which is
  the trap holding.
- ~~`What Lies Beneath` classified `coerced_or_assault`.~~ **Resolved
  2026-09-14** by the cast fix rather than by a taxonomy change. Once the
  classifier knew Ford plays Norman and Pfeiffer plays Claire, it classified the
  film `reciprocal_romance` and said why: the plot establishes them as a married
  couple, and "although the marriage is strained and Norman ultimately tries to
  murder Claire, the plot depicts an established reciprocal marital
  relationship". The earlier label was a symptom of not knowing who played whom.
  Whether intimate-partner violence should exclude a film outright is a rubric
  decision, recorded in the night log, not a taxonomy gap.
- **Ongoing episodes close at the run's as-of date.** That is a cutoff and the
  record says so, but it is not the same as a sourced `last_supported_active`,
  which nothing currently supplies. Six pilot episodes are affected.
  **Difficulty: medium.**
- ~~Two partners resolved to bare Q-ids.~~ **Fixed 2026-09-14**, and the cause
  was not the label SERVICE. Q13909 and Q2023710 have no English label in
  Wikidata at all, despite labels in dozens of other languages.

  **The scope was much wider than two.** Measured 2026-09-14 by
  `scripts/verify_identities.py`: **11 of the 100 roster members** have no
  English label -- Tom Cruise, Denzel Washington, Chris Hemsworth, Chris Evans,
  Chris Pratt, Angelina Jolie, Scarlett Johansson, Anne Hathaway, Mila Kunis,
  Emma Stone and Zendaya -- and 2 of the 14 pilot cohort. Any code that reads a
  label without falling back to the English Wikipedia sitelink is wrong about
  11% of the roster, and the two that surfaced were only the two whose names
  reached a printed report. Every one of the 114 ids is nonetheless the right
  person: 113 exact, and Chris Evans exact once the enwiki disambiguator
  "(actor)" is allowed for. Both carry
  English Wikipedia sitelinks naming them Angelina Jolie and Tom Holland, which
  is a sourced name rather than a guess, so that is the fallback. A person with
  neither stays unresolved and their episode stays excluded.
- ~~The same relationship enters the episode list twice, once from each side,
  and two episodes SHARE an id.~~ **Fixed 2026-09-14.** Found by
  `corroborate_relationships.py`, whose output keyed by `episode_id` silently
  lost a row and reported "22 of 30" over 31 episodes.

  The cause was simpler than the first diagnosis in this file, which claimed
  the two Wikidata items disagreed about the Affleck/Garner start date. They do
  not. When both halves of a couple are in the cohort, the fetcher reads the
  same statement off BOTH items and produces two candidates that agree on
  everything. `merge_progressions` groups by pair key but then saw two spans
  covering the same dates rather than two abutting ones, so it made two runs.
  Affleck + de Armas produced two rows with identical dates and therefore the
  identical `stable_id`.

  Exact duplicates now collapse before runs are formed -- same relation, same
  start, same end, with precision -- and the count is reported rather than
  swallowed. Two collapsed. 31 episodes became 29, and Affleck/Garner now
  merges correctly into one progression 2004-10 to 2018-10 instead of splitting
  into a dating span and a marriage. Statements that differ anywhere stay
  separate, because choosing between two disagreeing sources is the defect
  detector's business and not the merger's.

  **No conclusion moved**: jointly covered pairing-periods 4, distinct
  pairings 2, comparability 1 comparable and 3 shape-mismatched, all unchanged.
  The denominators did: `episodes_examined` 31 to 29, `candidate_pairings` 51
  to 49. `audit_doc_numbers.py` was not watching either, so a stale "of 51" sat
  in this file; both are rules now.

- ~~The doc audit counted rules that matched nothing as quantities checked.~~
  **Fixed 2026-09-14**, found while adding the two rules above. The summary
  printed `len(RULES)`, so a rule with no subject counted exactly as if it had
  verified something. Two rules had been dormant for some time --
  `coverage_saturation` and `cohort_coverage`, whose numbers now appear only in
  generated or historical documents, which are exempt -- so "16 quantities
  checked" meant 14. The rules are correct and worth keeping: each is proven
  against a sample phrase by `tests/test_doc_numbers.py`, and each will catch
  the number if it is ever typed into a hand-written document. What was wrong
  was the claim. The audit now names them and reports "15 of 18 quantities
  found and checked".

- **A dating-to-marriage progression only merges when the two spans abut
  within one day, and 7 in the roster corpus do not.** Found 2026-09-14 while
  fixing the mirrored duplicates above. `modules/records/episodes.py` opens by
  saying a progression "is ONE episode, not two scoring opportunities", and
  `JOIN_SLACK_DAYS = 1` delivers that only when Wikidata abuts the statements
  exactly. These seven do not, so each is two episodes:

  | Pair | dating | marriage |
  |---|---|---|
  | Mila Kunis + Ashton Kutcher | 2012– | 2015– |
  | Jennifer Lopez + Ojani Noa | 1996–1997 | 1997-02–1998-01 |
  | Jennifer Lopez + Marc Anthony | 2004-02–2004-03 | 2004-06-05–2014-06 |
  | Megan Fox + Brian Austin Green | 2004–2015-08-19 | 2010-06-24–2021-10-15 |
  | Scarlett Johansson + Colin Jost | 2017–2020 | 2020– |
  | Jennifer Lopez + Ben Affleck | 2021–2004 (sic) | 2022-07-16–2024 |
  | Jennifer Lopez + Cris Judd | 2001-09–2002-05 | 2001-09-29–2003-01 |

  Two of them overlap rather than abut, which a slack window cannot express at
  all: Megan Fox's dating span runs past the start of the marriage span, and so
  does Cris Judd's. The Ben Affleck row has an end before its start, the defect
  class already filed below, and it is the 2002-2004 relationship rather than
  the 2021 one.

  **Not widened here.** Raising `JOIN_SLACK_DAYS` changes which relationships
  are one scoring opportunity and which are two, which is a methodology
  decision with a published effect, not a parser tweak. The shapes above are
  also not all the same problem: a gap wants a slack window, an overlap wants a
  containment rule, and a reversed date wants the defect flag it already gets.
  **Difficulty: a decision, not a task.**

- **`data/roster100/run/joint_real_life.json` has no producer.** Found
  2026-09-14. Four scripts read it -- `scaling_report.py`,
  `reachable_products.py`, `score_roster_joint.py` and the chain's gate -- and
  nothing in the repository writes it. `packages/llmkit/artifacts.PRODUCERS`
  names `scaling_report.py`, which only reads it. `joint_coverage.py` takes
  `--bound` and `--out` and hardcodes the pilot paths, so it cannot produce the
  roster equivalent as it stands.

  The consequence is already visible. Its stored `scorable_episodes: 239` went
  stale when mirrored duplicates were collapsed, and `scaling_report.py` was
  reading its frozen roster figure beside a freshly computed pilot figure in
  the SAME table row. That row now computes both sides from the episodes
  artifacts, which is what fixed the disagreement, but the file's other
  fields -- `both_sides_have_evidence`, `jointly_covered_within_1y` and
  `comparability` -- are still frozen and still feed `docs/THE-TRAP.md`.

  The fix is to give `joint_coverage.py` the cohort and path flags the other
  roster-scale scripts already take, run it for the roster, and correct
  PRODUCERS. Not done tonight because regenerating it would move the numbers
  `THE-TRAP.md` publishes, and those should move under review rather than
  overnight. **Difficulty: medium, and it changes published figures.**

- ~~A film's release year was stored as January 1.~~ **Fixed 2026-09-14.**
  `fetch_onscreen_candidates.py` read `wdt:P577`, which returns a time with no
  precision, and sliced the literal to ten characters. Wikidata serialises a
  year-precision date as `+2002-01-01T00:00:00Z`, so 11 of the pilot's 20 films
  stored an invented January 1st -- in a project whose
  `packages/temporal/dates.py` exists to prevent exactly that.

  Every other query in the repository already used the statement path and read
  `wikibase:timePrecision`; this was the only one that did not. A test now
  fails on the PATTERN, not the instance: no `wdt:` path on any time-valued
  property. The next date property someone adds would have been written the
  same easy way.

  Selection was also arbitrary -- P577 repeats per country and the first SPARQL
  row won. A year statement now wins when one exists, otherwise the majority
  year and the earliest date within it. No year moved and nothing downstream
  changed.

- **One Wikidata episode has an end date before its start date.** Flagged,
  excluded, left exactly as sourced. Worth reporting upstream.
  **Difficulty: easy.**

## Coverage

- **Joint pairing coverage is 4 pairing-periods of 49 candidate pairings**,
  and only 1 of those 4 is shape-comparable. Person-period availability is no
  longer the binding constraint: the corpus now holds 42 observations over 9 of
  14 people. The constraint is that BOTH sides must be scorable over the SAME
  period, and prose extraction did not move it. **Difficulty: blocked on
  evidence.**
- ~~Rowspan continuation rows are skipped in award tables.~~ **Fixed
  2026-09-14, and the entry above was wrong about what the bug was.** It
  counted five dropped rows as one defect. Only three were rowspan
  continuations. The other two were the 2024 and 2025 Sexiest Man Alive
  winners, whose dates People now writes as `November 13, 2024` rather than
  `{{dts|...}}`. That second bug is the worse one: it takes the newest row
  every year, and it hides itself by shrinking the corpus instead of
  corrupting it, so the table looks merely short rather than wrong.

  A rowspan is now read, not guessed: `rowspan="3"` carries its date to
  exactly two following rows and no further, a row with its own date cancels
  an unfinished carry, and a row with no rowspan above it is still skipped.
  Continuation rows have one fewer cell, so the winner is read from the first
  cell rather than the second. Sexiest Man Alive parses 40 rows to 43 with 0
  skips, Most Beautiful 37 to 38. **The corpus did not change**: the same 41
  observation ids, none added, none removed, because none of the recovered
  winners is in the cohort or the partner universe. Four `ListEdition` records
  were added for the recovered years.

- ~~Unlinked winners are still dropped, and one is a real person.~~
  **Fixed 2026-09-14, and the ranked parser had the same hole.** Maxim names
  its 2006 winner, Eva Longoria, in plain text with no wiki-link, and the row
  was counted as a no-link skip. Looking for the same shape elsewhere found
  FHM's 2012 list writing rank 4 as `* <small>4th: Rosie Jones</small>`: that
  position vanished entirely, the year came out with nine entries instead of
  ten, and no statistic said so.

  Both parsers now read a plain-text cell when it looks like a name, and count
  it separately from a linked one. The strictness is the point -- a
  capitalised sentence, a single word, a cell still holding markup and a
  lowercase cell are all refused and stay COUNTED -- because a fabricated
  person in the corpus costs far more than a drop somebody can see. Emitting
  costs nothing either way: `to_records` and `ranked_to_records` only produce
  an observation for a name already in `name_to_person`.

  Every source table now reports zero skips. Three rows were recovered: Eva
  Longoria (Maxim 2006), Rani Hudson Fujikawa (People's Most Beautiful 2020,
  who also needed the rowspan fix to get a date at all) and Rosie Jones (FHM
  2012, rank 4). **The corpus did not change** -- the same 41 observation ids
  -- because none of the three is in the cohort or the partner universe.

- **The plan's "HTTP fetches <= 200, paced, breaker armed" is enforced
  nowhere.** Found 2026-09-14 by looking for functions with no caller, the
  class `refuse_mixed_contracts` belonged to. `Budget.spend_fetch` is called by
  nothing, and every `Budget` in the repository is built with `max_calls`
  alone.

  The reporting half is fixed: `max_fetches` defaulted to `10**9` and
  `report()` wrote it into every run artifact beside a `fetches_made` that was
  structurally zero, which reads as "fetches were counted and stayed under a
  limit". Neither half was true. The report is now silent about fetches until a
  budget exists or a fetch is spent, and `spend_fetch` counts even with no cap
  so telemetry arrives before anyone has to choose a number.

  The enforcement half is NOT done. Wiring a cap into the retrieval path would
  halt `run_chain.sh free` part-way through whenever the cap is low, and the
  right number is a judgement about how much of Wikipedia this project should
  pull in one run. The pieces are ready: pass `max_fetches` to a `Budget` and
  call `spend_fetch` in `packages/wiki/fetch.request` and
  `modules/records/wikidata._query`, which are now the only two places that
  reach the network. **Difficulty: easy to wire, but the number is a decision.**

- **Five plan-specified functions are implemented, tested, and called by
  nothing**: `count_like_diagnostic` and `with_baseline` / `cohort_median_partner`
  (plan section 4's Partner_WAR baseline and its count-like diagnostic),
  `gap_years` (the exact-arithmetic metric from example E), and
  `same_shape_view` (the same-shape board view). Mostly this is correct --
  M0 publishes no board, so a baseline it would be measured against is not due
  until the metric release -- but "tested" is quietly reassuring in a way that
  "runs" is not, and a later reader may assume they are wired up. Recorded so
  the next agent knows which capabilities exist only on paper.
  **Difficulty: not a task; a note.**

- **Two quota-produced artifacts predate tonight's record fixes and disagree
  with the live records.** `data/pilot/records/romance.json` carries film
  release dates in the old flattened form (`1993-01-01` for a year-precision
  source), and `data/pilot/run/evidenced_scores.json` still reports
  `max_fetches: 1000000000`. Both were written by scripts that spend model
  quota and cannot be re-run for free, so they keep the shape they had when
  they were made.

  Neither is used for anything that moved: the romance classifier keys on the
  film's Wikipedia page, not its date, and nothing reads the fetch fields. The
  next paid run of each drops both. Recorded so a reader comparing
  `romance.json` against `onscreen_candidates.json` does not read the
  difference as a bug in the live path. **Difficulty: resolves itself on the
  next re-score.**

- **Peter Horton was named one of People's "50 Most Beautiful People" and the
  corpus cannot use it.** Found 2026-09-14 by `absence_audit.py --source
  partners`, which flagged him `named_somewhere_investigate` because his own
  article names a permitted publisher. Investigating: *"During his run on
  Thirtysomething, People magazine named him one of the '50 Most Beautiful
  People.'"*

  There is no year. Thirtysomething ran 1987-1991, and the mention pins nothing
  inside that. The rubric's rule is "no usable dated evidence -> unscored", so
  the pipeline is right to hold nothing, and the flag did its job: it said
  look, and looking showed the absence was correct.

  It is recorded because it is the only lead in sixteen audited people and
  because it is a concrete example of the shape the evidence supply actually
  has. He is Michelle Pfeiffer's spouse 1981-1988, so a dated version of this
  one mention would make that pairing scorable on one side. **Difficulty:
  blocked on evidence, and the evidence is undated rather than missing.**

## Measurement (added late 2026-09-14)

- **The one comparable gap is 0.5 against a rank-shaped LSD of 1.03.** Daredevil
  2003, Affleck and Garner, both judged by an editorial award. Everything
  detectable is shape-mismatched. The 0.5 is the mean-of-two reducer, not a
  finding: fable gave Garner 93 and astra 92. **Difficulty: blocked on evidence.**
- **Shape confound is unmitigated.** 40% of the estimate is evidence type
  (omega-squared; the biased eta-squared reads 39%).
  Options not yet explored: restricting the board to same-shape pairings as the
  primary view rather than a scenario, or a within-shape calibration that would
  have to be disclosed as a modelling convention. **Difficulty: hard, and it is
  a methodology decision rather than a coding one.**
- **Rater noise rests on ONE judge family.** Six dossiers now, four repeats
  each, but codex hit 0% quota mid-run so all of it is `fable`. The plan chose
  two families specifically so a one-family idiosyncrasy could be told from a
  property of the rubric, and that check has never run on real evidence. Re-run
  with both when codex resets. **Difficulty: easy, blocked on quota.**
- **The award shape's noise is unmeasured, not zero.** Two dossiers, four
  repeats each, returned 92 eight times out of eight. That is much stronger
  than the original four-of-four but still cannot distinguish low variance from
  none, so no LSD is quoted for the shape. More dossiers would settle it.
  **Difficulty: easy, blocked on quota.**
- ~~`measure_rater_noise.py --account` hardcodes a config-dir path.~~
  **Fixed 2026-09-14.** All six quota-spending scripts defaulted `--account` to
  `/Users/tonygwu/.claude-e`, which that night was at 0% on its 5-hour window
  while another account had 66% fable headroom — a wrong default is worse than
  none, because the run fails as `auth_or_quota` and reads like a broken judge.
  There is no default now: `packages/llmkit/accounts.py` takes `--account` or
  `CELEB_ACCOUNT`, and otherwise refuses while naming the config directories it
  can see. Discovery globs rather than enumerating letters, so a new account
  needs no code change.
- **Nearby-period bound costs 2 pairing-periods.** Widening +/-1 to +/-2
  would take joint coverage from 2 to 4, and the count reaches 9 at +/-8 and
  goes no higher over the range measured — see the table in the M0 report's
  "Why joint coverage does not move". Not done, because a wider bound reuses an
  estimate further from the period it is supposed to describe, which is the
  manufactured precision the bound exists to prevent.
  **Difficulty: a decision, not a task.**
- ~~Partner gender is `unknown` for the whole partner universe.~~ **Fixed
  2026-09-14.** Sourced from Wikidata P21, which is a public-identity statement
  and not an inference: 12 female, 10 male, zero unknown across the pilot's 22
  partners. A person Wikidata does not record stays `unknown` rather than being
  defaulted, and an unknown must keep that person out of a gendered view rather
  than into a guess.

- ~~A stale rubric silently invalidated the whole corpus and nothing noticed.~~
  **Fixed 2026-09-14.** The grading contract is `sha256(rubric + schema)`, so a
  one-line typo fix in a rubric gives a new `contract_id` and every stored
  estimate was produced by a rubric that no longer exists. Nothing detected it.
  The scores stayed on disk, nine analysis scripts kept reading them, and every
  report kept presenting them as current. Three filed rubric corrections are
  waiting in this file to be applied together, so the next person to act on any
  of them would have hit this.

  `require()` now refuses an artifact whose `contract_id` no rubric on disk
  produces, naming the stale id, the rubrics that exist now, and
  `docs/CONTRACT-BUMP.md`. It is in the LOADER, not in the nine scripts,
  because a guard each caller must remember to invoke is a guard a new caller
  silently skips -- which is exactly what happened to `refuse_mixed_contracts`.
  The rubric list is globbed from `rubrics/*/`, so a fourth rubric needs no
  code change, and a directory without exactly one `.md` and one
  `.schema.json` is skipped rather than guessed at.

- ~~`refuse_mixed_contracts` still has no production caller.~~ **Closed
  2026-09-14 after an adversarial re-review. It must stay uncalled, for a
  stronger reason than was recorded here before: wiring it into this repository
  would be WORSE than leaving it alone, because on the record shape this
  pipeline actually writes it is a silent no-op.**

  The function keys on a per-record `contract_id`. No artifact in the corpus
  carries one. `score_evidenced.py`, `score_roster_joint.py`, `run_stress.py`
  and `measure_rater_noise.py` each stamp ONE `contract` block at the top of
  the file and write rows that carry `person`, `period`, `estimate`, `judges`
  and nothing about provenance. Measured over every artifact under `data/`:
  ten files carry a contract block, zero carry a per-record contract id. So

  ```
  refuse_mixed_contracts(evidenced_scores rows + romance.json rows)
  ```

  passes, although those two files record `ab015c99ad3e` (standing) and
  `7f82adbc0c79` (romance). Every row reads as `<no contract_id>`, the id set
  has one member, and the guard returns. A caller added today would buy a
  refusal that cannot fire and would read, to the next agent, as provenance
  that had been checked.

  The three fronts it was re-attacked on, and what they showed:

  1. **Does anything pool two scored artifacts?** Two scripts read more than
     one. `cross_run_stability.py` compares `evidenced_scores.json` with
     `joint_scores.json`, and refuses by hand at the artifact level.
     `evidence_density.py` reads `evidenced_scores.json` and
     `stress_report.json`, but keeps them in separate fields
     (`real_estimate_spread`, `synthetic_estimate_spread`) and pools nothing.
     No script concatenates estimate lists from two files.
  2. **Do two judge families create the pooling point?** No, and this is the
     argument that looked strongest and lost. `score_evidenced.py` builds ONE
     `GradingContract` and passes that same object to every judge, so fable and
     astra produce estimates under an identical contract id by construction.
     The contract records which BYTES were sent, not who answered. The existing
     `value = sum(per_judge.values()) / len(per_judge)` is a real pooling point
     and has been live since before M0, but it pools across families under one
     contract, which is what `across_judges_gap` and `needs_adjudication` are
     for. Adding the second family changes nothing the mixing guard can see.
  3. **Does the rubric bump create it?** No. A bump moves the id, so every
     stored artifact goes stale, and `refuse_stale_contract` inside `require()`
     catches that on the first read. Verified against the live tree while the
     bundled pass was uncommitted in it: reading `evidenced_scores.json` exits
     naming `ab015c99ad3e` and the three ids the new rubrics produce.

  Keep the function and its tests. The next thing that genuinely pools will
  need a guard, but it will need one shaped for ARTIFACTS rather than records.
  **Difficulty: not a task; recorded so it is not re-filed a third time.**

- ~~`write_m0_report.py` and `audit_doc_numbers.py` read scored artifacts
  without the contract check.~~ **Fixed 2026-09-14**, same day it was filed,
  by the reviewer who found it while attacking W072.

  Both now call `refuse_stale_contract`. `write_m0_report.load` keeps its
  optional-default behaviour, because a missing roster-scale artifact is
  legitimate: absent is allowed, stale is not.

  Two more things were fixed with it, because the two named scripts were
  instances rather than the defect. `scripts/run_chain.sh` now refuses the
  whole report pass when any artifact is stale, instead of recording each
  refusal and running on to the renderer. And
  `tests/test_no_guard_bypass.py` asserts the CLASS: every script that reads
  a JSON artifact either goes through `require` or calls the guard, with an
  explicit exemption list that must carry a reason.

  Superseded text follows.

  **`write_m0_report.py` and `audit_doc_numbers.py` read scored artifacts
  without `require()`, so the stale-contract guard does not cover the report.**
  Found 2026-09-14 while re-reviewing the item above. The stale guard was put
  inside the loader precisely so no script has to remember it, and these two
  bypass the loader: `write_m0_report.py` defines its own `load()` that calls
  `json.loads(f.read_text())`.

  This is live right now. `scripts/run_chain.sh` sets `-uo pipefail`, not `-e`,
  and its `run()` helper records `fail=1` and CONTINUES. So after a rubric bump
  `bash scripts/run_chain.sh reports` fails every `require()`-based stage,
  keeps going, and still reaches `write_m0_report.py` at the end, which
  regenerates `docs/M0-REPORT.md` from the stale corpus and exits the chain
  non-zero for reasons a reader will attribute to the earlier stages. That is
  the quiet wrong answer the stale guard was written to stop, arriving through
  the one script whose whole output is the deliverable.
  **Difficulty: easy — route both through `require()`.**

- ~~The M0 report compares numbers across separate scored artifacts with no
  contract check.~~ **Fixed 2026-09-14.** `run_stress.py` reads the
  rater-noise floor from a separate scoring run and compared this run's
  spread against it. It now refuses a stale floor, and the check sits
  OUTSIDE the `try` that swallows read errors, which is where a silent
  `return None` would otherwise have hidden it.
  `measure_rater_noise.py --recompute` had the same hole and got the same
  fix.

  Superseded text follows.

  **The M0 report compares numbers across separate scored artifacts with no
  contract check.** `spread_verdict()` judges a spread from
  `stress_report.json` against a noise floor from `rater_noise.json`, and the
  evidence-density table prints `real_estimate_spread` (from
  `evidenced_scores.json`) beside `synthetic_estimate_spread` (from
  `stress_report.json`). All four artifacts happen to share one contract today,
  so nothing is wrong now. Nothing enforces it. If a partial re-score ever
  leaves two of them on different rubrics, a rubric difference is published as
  a format effect. This, not record pooling, is the guard the invariant
  actually still wants: assert that a set of ARTIFACTS share a contract id,
  taking the top-level `contract` blocks rather than per-row fields.
  **Difficulty: easy to write; the decision is which artifact sets must match.**

- ~~`person_period_scores.json` carries 39 estimates and no contract block.~~
  **Fixed 2026-09-14.** `score_evidenced.py` now stamps the contract onto the
  checkpoint as well as the final artifact, and
  `tests/test_stale_contract.py` asserts both files carry one.

  The related hardcoded-path defect was fixed with it: the currency test
  listed five artifacts by name and missed `pilot_report.json` and
  `rater_noise.json`, both of which carry a contract block. It globs now.
  That is the second time in this repo a hardcoded set of paths went stale
  after the set grew.

  Superseded text follows.

  **`person_period_scores.json` carries 39 estimates and no contract block at
  all.** `score_evidenced.py` writes it as a crash-recovery checkpoint before
  the pairings step, and writes `{person_periods, failures, halted}` with no
  `contract` key. `refuse_stale_contract` returns early on an artifact with no
  contract block, and `refuse_mixed_contracts` sees no per-row id, so BOTH
  guards are no-ops on it. Nothing reads it today, which is the only reason
  this is small. Its `history/` copies have the same hole.
  **Difficulty: trivial — stamp the contract block on the checkpoint too.**

- ~~`contract_id` concatenates its parts with no separator.~~ **Fixed
  2026-09-14** at the bundled contract bump. Each part is now prefixed with
  its byte count, so moving text across the rubric/schema boundary changes
  the id. `tests/test_contract_id_boundary.py` reconstructs the old scheme
  and asserts it really did collide, so the test shows what it fixed rather
  than only that the new one works.

  The scheme change moved all three ids, including romance's, whose bytes
  did not move. A reader could not otherwise tell a scheme change from a
  rubric change, so `contract_id_scheme` is now stamped beside the id in
  every artifact.

  Superseded text follows.

  **`contract_id` concatenates its parts with no separator.** Moving text from
  the end of the rubric to the start of the schema leaves the contract id
  unchanged, so two genuinely different contracts could share an identity. Not
  fixed now: the corpus records `ab015c99ad3e`, the plan forbids pooling
  estimates across contract ids, and a length-prefixed hash would make every
  existing estimate look like it came from a different contract. **Do it at the
  next rubric version bump, when the id changes anyway.**
  **Difficulty: easy, but must be bundled.**

- ~~`CodexJudge`'s docstring contradicted its own implementation about what
  `effort_took_effect` means.~~ **Fixed 2026-09-14.**

  The class docstring said a zero `reasoning_output_tokens` count meant "the
  request was not served as asked". The measurement note beside the field, 60
  lines below, said the opposite and carried the evidence: turns of 234-257
  output tokens reported zero while an identical-shaped probe reported 27, so
  the count cannot separate "effort did not take effect" from "this turn needed
  little reasoning".

  **It cost a wrong conclusion the same day.** An analysis of the first
  two-family re-score read the docstring, found 18 of 40 astra verdicts flagged,
  and reported that nearly half the cross-family comparison had been mis-served.
  That had not been shown. The docstring now states the disclaimer and records
  why, and `tests/test_effort_flag_is_not_a_verdict.py` asserts the flag is
  never read as a verdict and that the measurement behind the disclaimer
  survives.

  **The open question is untouched by that fix.** The flag splits the corpus
  hard -- mean cross-family gap 0.39 where it is false against 2.64 where it is
  true -- and it is nearly collinear with evidence shape, 14 of 18 award-shaped
  dossiers falling on the false side. Two readings fit: astra got cheaper
  responses on those dossiers, or a one-winner award needs no reasoning BECAUSE
  it is pinned by construction, which is the shape finding arriving by another
  route. n = 40 cannot separate them. **Difficulty: needs a designed probe, not
  more of the same corpus.**

- **`ADJUDICATION_GAP = 10.0` is still the plan's provisional value — and the
  data to set it now exists.** **Unblocked 2026-09-15** by the two-family
  re-score. The threshold itself is a methodology decision and is left to the
  operator.

  **Observed cross-family gaps**, 40 of 40 person-periods, where every one was
  previously `None`: median 1.0, mean 1.62, max **8.0**, 18 exact agreements.
  So 10.0 flags nothing, exactly as this entry predicted when it was filed.

  **The quantity to set it against is within-family noise, not a percentile of
  the gaps.** A percentile fixes the flag rate by construction whatever the
  judges do. The repeat measurement gives the meaningful comparison: each family
  is highly self-consistent on byte-identical dossiers (ranked within-judge sd
  0.00-0.82, mean 0.371) while differing from each other by 0.5 to 2.25 on those
  same dossiers. Disagreement is real and is several times each family's noise
  about itself.

  | candidate | basis | flags (all 40) | flags (22 effort-verified) |
  |---|---|---|---|
  | 1.03 | the rank-shaped LSD itself | 14 | 12 |
  | 2.06 | 2x that LSD | 8 | 8 |
  | 5.0 | round, below the observed max | 4 | 4 |
  | 6.0 | only the clearest disagreements | 2 | 2 |
  | 10.0 | unchanged | 0 | 0 |

  **Two caveats before anyone picks one.** The noise floor is itself unstable:
  measured twice on the same four dossiers it gave 2.56 and 1.03, so any
  candidate derived from it inherits a factor-of-three uncertainty. And 18 of 40
  astra verdicts carry `effort_took_effect: false`, whose meaning is unresolved
  (see the CodexJudge entry above), which is why the table reports the
  effort-verified subset separately. **Difficulty: a decision, now informed.**

- ~~`ADJUDICATION_GAP = 10.0` is still the plan's provisional value.~~
  **Superseded by the entry above.** The plan
  set it "provisionally 10 points, set from M0's own spread", and M0 has now
  measured a spread: the rank-shaped least significant difference is 2.56
  points. Ten is more than four times that, so a real cross-family disagreement
  could sit well inside it and never be flagged.

  Not changed, because the data that should set it did not exist. Every
  across-judge gap in the corpus was `None`: codex ran out of quota and one
  family scored every person-period, so nothing had ever exercised this
  threshold. Set it from the observed distribution of cross-family gaps AFTER a
  two-family re-score, not from the single-family repeat noise, which measures
  a different thing. **Difficulty: a decision, blocked on the re-score.**

  *The count is deliberately not written here.* This paragraph is history, and
  a historical count reads identically to a current one to
  `scripts/audit_doc_numbers.py`, which flagged it as stale against the corpus
  that has since grown.

- **Identity leakage is measurable in the fable arm: 4 points.** S6 attaches the
  same evidence to the real name, to an anonymised subject, and to a swapped
  name. Plan v3 §6.3 requires all three to score the same.

  | arm | fable | astra |
  |---|---|---|
  | named | 76 | 82 |
  | anonymised | 80 | 83 |
  | swapped_name | 80 | 84 |

  Both families move in the SAME direction -- naming the real person lowers the
  estimate -- which a single-family run could not have shown. fable moves 4
  points, above the noise floor on either measurement; astra moves 2.

  One dossier per arm, so this is a signal to investigate rather than an effect
  size. **What would settle it: several dossiers per arm, and the anonymised
  arm checked for whether it removed anything besides the name.**
  **Difficulty: medium, costs a stress re-run.**

- **Copy volume alone moved the estimate by 2 points (S8).** One copy scored 72,
  five identical syndicated copies scored 70. The plan requires syndication to
  change nothing.

  This does NOT contradict the deterministic test that five syndicated copies
  leave `distinct_original_sources` at 1 with the cached score inputs
  byte-identical. That test checks the PIPELINE arithmetic and it passes. S8
  checks the JUDGE, which sees the dossier text, and the judge moved. Two
  different claims that read alike in prose.
  **Difficulty: medium; the fix is probably dossier rendering, not the rubric.**

- **Every stress verdict is a binary call against an unstable floor.**
  `verdict()` renders "within" or "ABOVE the measured floor", where the floor is
  the max per-shape LSD. That floor measured 2.56 on one run and 1.03 on the
  next, from the same judge on the same four dossiers.

  The verdicts flip: under 2.56 only S2 and S6-fable read ABOVE; under 1.03, S2,
  S6, S7 and S8 all do. The number of significant stress findings doubles on a
  quantity that is not pinned at four dossiers by four repeats.

  **What would fix it: more repeat targets, and reporting the spread against an
  INTERVAL for the floor rather than a point.** Until then, read the spreads and
  the floor together, never the verdict alone. **Difficulty: medium.**

- **Stress case S2 tests anchor-following, not format equivalence.** Its prose
  arm is the VERBATIM text of the rubric's calibration Example 3, anchored at
  88, and its award arm has the shape of Example 1, anchored at 92. The judge
  returned 92, 92, 88 — the anchored values. So the 4-point "format effect" is
  the rubric telling the judge where those formats sit, not a measurement that
  the same substance is perceived differently when published differently.

  Rebuild the arms from a judgment that appears in NO calibration example, and
  keep the three renderings substantively identical to each other. Until then
  the case is still worth running — a judge that stopped following its anchors
  would be a real finding — but it must not be quoted as evidence about format.
  **Difficulty: easy, but it costs a stress re-run (~27 calls).**

- ~~`rubrics/mentions/MENTIONS.md` lists an undated example it then forbids.~~
  **Fixed 2026-09-14.** `mentions-1.0` became `1.1`.

  The filed item named ONE undated example. There were two:
  `tests/test_rubric_self_consistency.py` was written to catch the filed one
  and failed on `"ranked 5th in FHM's 100 Sexiest Women"` as well, which no
  human reader had noticed. A rule stated as a rule catches more than the
  instance that prompted it. Both now carry a year.

  Superseded text follows.

  **`rubrics/mentions/MENTIONS.md` lists an undated example it then forbids.**
  "What to extract" includes *"voted the sexiest man in a readers' poll"*,
  which carries no year, while rule 3 says "Never infer a year. If the sentence
  does not carry one, skip it." A judge following the examples and a judge
  following the rules would disagree about that one.

  Not changed now: the rubric is part of the hashed extraction contract, so
  editing it changes the contract id and the stored prose mentions were
  extracted under the old one. Bundle it with the next rubric version bump,
  alongside the `contract_id` boundary item above, when the id changes anyway.
  **Difficulty: trivial, must be bundled.**

- ~~`estimate.schema.json` declares two fields nullable that its own enums
  forbid.~~ **Fixed 2026-09-14.** `null` is in both enums.

  The blast radius was measured before and after rather than reasoned about:
  under the pre-fix schema **52 of 52** stored judge verdicts failed
  validation; under the fixed one, 0 of 52. `jsonschema` is now a pinned
  dependency and `tests/test_schema_validates_corpus.py` validates every
  stored verdict, so the landmine became a gate. That test also reconstructs
  the pre-fix schema and asserts it still rejects everything, so a silent
  revert cannot pass.

  Superseded text follows.

  **`estimate.schema.json` declares two fields nullable that its own enums
  forbid.** `missingness_reason` and `band` both carry
  `"type": ["string", "null"]` alongside an `enum` that does not list `null`.
  JSON Schema keywords are conjunctive: an instance must satisfy `type` AND
  `enum`, so `null` is invalid for both despite the type.

  Every SCORED record sets `missingness_reason` to null, correctly. So under
  strict validation essentially every record in the corpus would be rejected.

  **Nothing validates against this schema today** — it is read as bytes for the
  contract hash and shown to the judge, and `parse_verdict` does its checks by
  hand — so nothing is broken. It is a landmine: **do not add jsonschema
  validation without fixing the enums first**, or the first thing it will do is
  reject the entire corpus.

  The fix is to add `null` to both enums. Not done now because the schema is
  part of the hashed contract; bundle it with the next version bump alongside
  the other two contract items above. **Difficulty: trivial, must be bundled.**

## Tooling

- ~~Smoke tests can clobber production artifacts.~~ **Fixed 2026-09-14.**
  `packages/llmkit/outputs.guard_output` refuses a write whose declared quality
  field is strictly lower than the existing artifact's, naming both values and
  saying to use `--out` or `--force`. Wired into `measure_rater_noise.py` after
  the dry-run return, so a dry run is never blocked. The guard is deliberately
  narrow: one declared field, strictly-lower only, because a guard that judges
  overall richness will eventually block a legitimate write and teach everyone
  to pass `--force` by reflex.
- **CI is configured and has never once executed.** `.github/workflows/tests.yml`
  was added 2026-09-14 and treats any non-zero exit as failure, pytest's 5
  included. Every one of its runs has been refused at GitHub's billing gate in
  about 2 seconds, before reaching pytest.

  So the workflow file itself is untested, and the repository's Actions state
  reads **red while the suite is green** — which is worse than having no CI,
  because a red badge that means "billing" looks exactly like a red badge that
  means "the tests fail".

  Two routes clear it, and they are not equivalent. Settling the account's
  Actions billing fixes it for a private repository. **Making the repository
  public also fixes it**, because Actions minutes on public repositories are
  free on standard runners — so if this repository is published, this entry
  closes by itself and the badge starts telling the truth.

  Simulated on 2026-09-16 rather than assumed, because the workflow has still
  never run for real: fresh clone with no `data/`, `python3 -m venv`,
  `pip install -r requirements.txt`, `python -m pytest tests -q`. It FAILED on
  `test_there_are_verdicts_to_validate`, which asserts a corpus that `data/`
  being gitignored guarantees is absent. Fixed; the same simulation now exits 0
  on Python 3.12.4 and 3.14.7 with 1020 passed, 83 skipped.

  Until the gate actually runs, **the real gate is local**:
  `.venv/bin/python -m pytest tests -q`.

  **The workflow file itself is no longer untested** (2026-09-14). It cannot be
  run, so it is checked instead. `tests/test_ci_workflow.py` asserts the parts
  that would silently stop the gate from gating: `python -m pytest` rather than
  a bare `pytest` off PATH, an install from `requirements.txt` that exists, no
  pipe or `|| true` swallowing pytest's exit status, a pinned 3.12, a trigger
  that fires, and no test in the suite making a live HTTP call. Each is
  mutation-tested.

  The workflow was also simulated end to end by hand: a fresh clone,
  `python3 -m venv`, `pip install -r requirements.txt`, `python -m pytest tests
  -q` exits 0 with 656 passed and 49 skipped -- and exits 0 again with the
  network blocked behind an unroutable proxy, which is what the workflow's
  "offline and deterministic" comment claims.

  So when billing is cleared, the first run should be green rather than a
  surprise. **Difficulty: still blocked on the operator, but only on billing.**
- **No page-weight or export tooling**, because there is no site yet.
  **Difficulty: deferred until there is a board worth rendering.**

## Public release: what is still open (2026-09-16)

Filed by the pre-publication audit. The repository is **not** public and
whether it becomes public is the operator's decision alone. Nothing in this
section was actioned; each item needs a judgement this audit could not make.

The secrets scan came back clean. No API key, token, OAuth credential, `.env`
file, private key or account credential has ever been committed, across all 252
commits at the time of the audit. Every commit author is the GitHub noreply
address. No `data/` path and no `.tsv`/`.tsv.gz` has ever been in history, and
the largest blob ever committed is 119 KB. Those categories are closed.

### B1. RESOLVED 2026-09-16 — the email is gone from every clone and from origin

The message of `9234a510` was rewritten to redact the account id and address, and
the 9 commits from it to HEAD were replayed. Verified afterwards: 0 occurrences on
`main`, 0 on `origin/main`, 0 in repo-0/1/2/3 after re-syncing them, and
`git diff backup main` was EMPTY, so only messages changed and no content moved.
All three sibling clones held 0 unpushed commits, so the force-push discarded
nobody's work. `refs/original` and the backup branch were deleted and the reflog
expired, or the old message would have survived locally.

~~Original entry:~~ 

**Caused by this audit, in the commit that fixed the underlying problem.**
`9234a510` quotes `.wrangler/cache/wrangler-account.json` verbatim to explain
why `.wrangler/` had to be ignored. That quote carries the Cloudflare account
id and, as the account NAME, a personal gmail address. Neither is reproduced
here, for the same reason they should not be in a commit message. It is in that
message body only. No tracked file has ever contained either, and `git grep`
over every revision returns nothing.

Read it with `git log -1 9234a510` if you need to see the exact strings.

This defeats part of the reason AGENTS.md sets the noreply author address:
"so the history never needs an author rewrite if the repository is made public
later".

A rewrite was deliberately NOT attempted. It would move six commits, one of
them another agent's, and rule 8 forbids force-pushing `main`. It has to be
coordinated across `repo-1`..`repo-3` or done when no other agent is working.

**The cost of this item only goes up.** Fixing it now costs one coordinated
rewrite. After publication it cannot be fixed at all, because forks, caches and
archives keep the old message.

### B2. RESOLVED 2026-09-16 — MIT, the operator's choice. See `LICENSE`.

~~Original entry:~~ 

`git grep` finds no licence statement in any tracked file and `pyproject.toml`
has no `license` field. A public repository with no LICENSE grants nobody any
permission, which is legal but usually not what was intended. README.md and
CONTRIBUTING.md both say so plainly rather than leaving it silent. Choosing one
is an operator decision.

### B3. CLOSED 2026-09-16 — the operator decided not to drop anyone

**Decided with the measurement in hand, not in the abstract.** Wikidata occupation
(P106) puts 26 of the 281 people on the real-life side outside any performing
occupation: spouses such as Luciana Barroso, Cooke Maroney and Katherine
Schwarzenegger, plus athletes and businesspeople.

Two rules were measured. Dropping a pairing when either side is a non-performer
cuts 27 pairings and removes Cameron Diaz, Keanu Reeves, Will Smith, Chris Pratt
and five others from the board — it punishes the celebrity for the privacy of the
non-celebrity, which is backwards. Declining to RANK non-performers while keeping
them as partners costs 0 pairings and removes exactly ONE person, Alex Rodriguez,
who is a public figure. The operator judged that not worth doing.

**Two earlier framings of this were wrong and are recorded so they are not
repeated.** Ojani Noa and Cris Judd were named as private individuals; P106 says
model and dancer/choreographer, both performers. And a first measurement used
"has an on-screen pairing in this corpus" as the performer test, which labelled
Amy Poehler, Lupita Nyong'o, Megan Fox and Ana de Armas non-performers — the
on-screen corpus only covers the 30 seeds' films, so it is not a test of what
anyone does for a living.

If this is ever reopened, the cheap half-step is initials for non-performers in
the expanded detail: it keeps every number and removes the name.

~~Original entry:~~ 

`docs/BOARDS.md` publishes attractiveness rankings of real named people, and
says of itself that no source backs any number in it. Several partners named
there are private individuals known publicly only as somebody's former partner,
not public performers.

This is the highest-reputational-risk content in the repository and it is a
product-policy question, not a tidiness one. **It was not changed**, because
AGENTS.md is explicit that nobody is removed from the roster by name, and
picking people to delete is exactly the roster-selection-for-presentation that
`docs/SOURCE-HUNT.md` warns against.

Note that `scripts/deploy_site.sh` now publishes a board to a public URL, so
this question is partly live whatever the repository's visibility is.

### B4. Judge and model identifiers may not be public names

`fable`, `astra`, `gpt-6-astra`, `claude-fable-5-1`, `claude-opus-5` and
`claude-sonnet-5` appear throughout the code, the artifacts and `web/board.html`.
If any is an unreleased or internal vendor codename, publishing the repository
publishes it. This audit could not determine that. Confirm before publishing.

### B5. RESOLVED 2026-09-16 — files moved out; the operator is deleting the Figma file

`docs/design/FIGMA-HANDOFF.md` and `.app-ux-design/` moved to `../design-private/`,
outside every checkout, and both paths are gitignored. The key remains in history
from `7cef44f` onward, across 51 commits. No rewrite is needed: the operator is
deleting the Figma file itself, which makes the key an identifier pointing at
nothing. A file key is a capability, not a credential — what it opens depends on
that file's sharing settings — so retiring the file is a complete fix and a
51-commit rewrite is not.

~~Original entry:~~ 

`docs/design/FIGMA-HANDOFF.md`, `.app-ux-design/design-brief.md` and
`.app-ux-design/state-ledger.json` all carry the same Figma file key, which is
already in those tracked files and is therefore not repeated here. The URL
alone grants no access. It does reveal the
file exists, and it becomes a working link for anyone if that file's sharing is
ever set to "anyone with the link". The key has no value to an outside reader.

### Smaller items, none of them blocking

- **248 commit messages carry a `claude.ai/code/session_...` URL.** Those links
  are not usable by a reader and cannot be removed without rewriting nearly the
  whole history. Accept them, or rewrite once and never add another.
- **`docs/design/FIGMA-HANDOFF.md` states stale numbers under the heading
  "Immutable product facts a future session must not contradict".** It says
  evidence shape explains **31%**; the current measured figure is 40%
  omega-squared. `scripts/audit_doc_numbers.py` has no rule matching that
  phrasing, so it did not catch it. Either regenerate the section or mark it as
  a dated snapshot.
- **`scripts/rebuild_boards.py` and `scripts/refresh_boards.sh` default to
  writing `~/Desktop/punching-above-weight.html`.** Convenient for one machine
  and a poor default for a stranger who clones the repository. Left alone
  because changing it would change a workflow this audit did not own.
- **`tests/fixtures/quotapick_pick_all_exhausted.json` still names the
  operator's subscription accounts** (`claude`, `claude_b`..`claude_d`, `codex`,
  `cursor`) with their quota remaining at capture time. The absolute home path
  was neutralised in `1d59c1c`; the account topology was kept because the
  capture's realism is its value and AGENTS.md discusses those account names
  openly anyway. Revisit only if that topology is considered private.
