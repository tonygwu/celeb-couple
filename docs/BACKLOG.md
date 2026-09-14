# Backlog

Filed by the overnight run of 2026-09-14. Difficulty tags are estimates.

See also `docs/BACKLOG-roster.md` for roster scope and the evidence-source hunt.

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
- **Rowspan continuation rows are skipped** in award tables: 3 in Sexiest Man
  Alive, 2 in Most Beautiful. They carry no date cell, so they are dropped
  rather than mis-dated. None was a cohort member. **Difficulty: easy.**

## Measurement (added late 2026-09-14)

- **The one comparable gap is 0.0 against a rank-shaped LSD of 2.4.** Daredevil 2003,
  Affleck and Garner, both judged by an editorial award. Everything larger is
  shape-mismatched. **Difficulty: blocked on evidence.**
- **Shape confound is unmitigated.** 39% of the estimate is evidence type.
  Options not yet explored: restricting the board to same-shape pairings as the
  primary view rather than a scenario, or a within-shape calibration that would
  have to be disclosed as a modelling convention. **Difficulty: hard, and it is
  a methodology decision rather than a coding one.**
- **Rater noise rests on one judge and two dossiers.** Codex hit 0% quota
  mid-run. Re-run with both families when it resets in ~5 days.
  **Difficulty: easy, blocked on quota.**
- **The award shape's noise is unmeasured, not zero.** Four repeats all returned
  92, which cannot distinguish low variance from none, so no LSD is quoted for
  it. More repeats would settle it. **Difficulty: easy, blocked on quota.**
- **`measure_rater_noise.py --account` hardcodes `/Users/tonygwu/.claude-e`.**
  The account list should be derived from `quotapick status`, not typed: the
  operator's own notes record four separate places that broke when an account
  was added. **Difficulty: easy.**
- **Nearby-period bound costs 2 pairings.** Widening +/-1 to +/-2 would take
  joint coverage from 2 to 3 distinct pairings, saturating at 6. Not done,
  because a wider bound reuses an estimate further from the period it describes.
  **Difficulty: a decision, not a task.**
- ~~Partner gender is `unknown` for the whole partner universe.~~ **Fixed
  2026-09-14.** Sourced from Wikidata P21, which is a public-identity statement
  and not an inference: 12 female, 10 male, zero unknown across the pilot's 22
  partners. A person Wikidata does not record stays `unknown` rather than being
  defaulted, and an unknown must keep that person out of a gendered view rather
  than into a guess.

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
