# Backlog

Filed by the overnight run of 2026-09-14. Difficulty tags are estimates.

See also `docs/BACKLOG-roster.md` for roster scope and the evidence-source hunt.

**Three items below are waiting on a single rubric/schema version bump.** Each
one alone costs a full re-score, so they should go together:
`estimate.schema.json`'s nullable enums, the `contract_id` boundary ambiguity,
and the `MENTIONS.md` example that contradicts rule 3. The procedure is in
[`docs/CONTRACT-BUMP.md`](CONTRACT-BUMP.md).

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
  Wikidata at all, despite labels in dozens of other languages. Both carry
  English Wikipedia sitelinks naming them Angelina Jolie and Tom Holland, which
  is a sourced name rather than a guess, so that is the fallback. A person with
  neither stays unresolved and their episode stays excluded.
- **One Wikidata episode has an end date before its start date.** Flagged,
  excluded, left exactly as sourced. Worth reporting upstream.
  **Difficulty: easy.**

## Coverage

- **Joint pairing coverage is 4 pairing-periods of 51 candidate pairings**,
  and only 1 of those 4 is shape-comparable. Person-period availability is no
  longer the binding constraint: the corpus now holds 41 observations over 9 of
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

- **Unlinked winners are still dropped, and one is a real person.** Maxim's
  2006 row names `Eva Longoria` in plain text with no wiki-link, so it is
  counted as `skipped_no_link`. The existing reasoning holds in general -- a
  plain-text cell is usually a note, and inventing a person from one is the
  quiet wrong answer this project exists to avoid. But `to_records` only emits
  an observation for a winner already in `name_to_person`, so matching plain
  cell text against the KNOWN roster names would invent nothing: either it is
  an exact match for a person we already track, or it is dropped as now.
  Not done tonight because it changes a shared parser and yields zero
  observations today -- neither Longoria nor the other unlinked row (an
  infant, correctly unlinked) is in any roster. **Difficulty: easy.**

## Measurement (added late 2026-09-14)

- **The one comparable gap is 0.0 against a rank-shaped LSD of 2.56.** Daredevil 2003,
  Affleck and Garner, both judged by an editorial award. Everything larger is
  shape-mismatched. **Difficulty: blocked on evidence.**
- **Shape confound is unmitigated.** 31% of the estimate is evidence type
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

- **`refuse_mixed_contracts` still has no production caller, and that is the
  correct state.** It was filed as a gap. Investigating it found the premise
  was incomplete: the function refuses to POOL records from different
  contracts, and nothing in this codebase pools two scored artifacts. The one
  place that reads two of them, `cross_run_stability.py`, already refuses by
  hand, and its message is better than the generic one because it can say what
  the comparison was FOR. The real exposure was staleness rather than mixing,
  and that is the item above. Keep the function: the first script that
  genuinely pools will need it, and a test asserts it refuses an unlabelled
  record rather than skipping it. **Difficulty: not a task; recorded so it is
  not re-filed.**

- **`contract_id` concatenates its parts with no separator.** Moving text from
  the end of the rubric to the start of the schema leaves the contract id
  unchanged, so two genuinely different contracts could share an identity. Not
  fixed now: the corpus records `ab015c99ad3e`, the plan forbids pooling
  estimates across contract ids, and a length-prefixed hash would make every
  existing estimate look like it came from a different contract. **Do it at the
  next rubric version bump, when the id changes anyway.**
  **Difficulty: easy, but must be bundled.**

- **`ADJUDICATION_GAP = 10.0` is still the plan's provisional value.** The plan
  set it "provisionally 10 points, set from M0's own spread", and M0 has now
  measured a spread: the rank-shaped least significant difference is 2.56
  points. Ten is more than four times that, so a real cross-family disagreement
  could sit well inside it and never be flagged.

  Not changed, because the data that should set it does not exist. Every
  across-judge gap in the corpus is `None`: codex ran out of quota and one
  family scored all 39 person-periods, so nothing has ever exercised this
  threshold. Set it from the observed distribution of cross-family gaps AFTER a
  two-family re-score, not from the single-family repeat noise, which measures
  a different thing. **Difficulty: a decision, blocked on the re-score.**

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

- **`rubrics/mentions/MENTIONS.md` lists an undated example it then forbids.**
  "What to extract" includes *"voted the sexiest man in a readers' poll"*,
  which carries no year, while rule 3 says "Never infer a year. If the sentence
  does not carry one, skip it." A judge following the examples and a judge
  following the rules would disagree about that one.

  Not changed now: the rubric is part of the hashed extraction contract, so
  editing it changes the contract id and the stored prose mentions were
  extracted under the old one. Bundle it with the next rubric version bump,
  alongside the `contract_id` boundary item above, when the id changes anyway.
  **Difficulty: trivial, must be bundled.**

- **`estimate.schema.json` declares two fields nullable that its own enums
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
  included. Every one of its 30 runs has failed in about 2 seconds with:

  > The job was not started because recent account payments have failed or your
  > spending limit needs to be increased.

  So the job is blocked at GitHub's billing gate and never reaches pytest. The
  workflow file itself is untested, and the repository's Actions state reads
  **red while the suite is green** — which is worse than having no CI, because
  a red badge that means "billing" looks exactly like a red badge that means
  "the tests fail".

  Only the operator can clear this: Settings → Billing & plans. Private
  repositories consume billable Actions minutes, and this one must stay
  private, so going public is not the workaround.

  Until then **the real gate is local**: `.venv/bin/python -m pytest tests -q`.
  **Difficulty: blocked on the operator.**
- **No page-weight or export tooling**, because there is no site yet.
  **Difficulty: deferred until there is a board worth rendering.**
