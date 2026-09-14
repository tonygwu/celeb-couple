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
- **`What Lies Beneath` was classified `coerced_or_assault`** in the pre-cast
  run. Correct to exclude,
  but the pair are also a married couple for most of the film. The taxonomy has
  no way to say "a relationship that the plot later turns into an assault", and
  flattening it to one label loses information. **Difficulty: medium.**
- **Ongoing episodes close at the run's as-of date.** That is a cutoff and the
  record says so, but it is not the same as a sourced `last_supported_active`,
  which nothing currently supplies. Six pilot episodes are affected.
  **Difficulty: medium.**
- **Two partners resolved to bare Q-ids** (`Q13909`, `Q2023710`) because the
  Wikidata label service returned no English label. Flagged as a defect and
  excluded, not guessed. **Difficulty: easy.**
- **One Wikidata episode has an end date before its start date.** Flagged,
  excluded, left exactly as sourced. Worth reporting upstream.
  **Difficulty: easy.**

## Coverage

- **Joint pairing coverage is 1 of 51 candidate pairings.** Person-period
  availability is 13 observations over 9 of 14 people; the binding constraint is
  that both sides must be scorable over the same period. **Difficulty: blocked
  on evidence.**
- **Rowspan continuation rows are skipped** in award tables: 3 in Sexiest Man
  Alive, 2 in Most Beautiful. They carry no date cell, so they are dropped
  rather than mis-dated. None was a cohort member. **Difficulty: easy.**

## Measurement (added late 2026-09-14)

- **The one comparable gap is 0.0 against an LSD of 1.2.** Daredevil 2003,
  Affleck and Garner, both judged by an editorial award. Everything larger is
  shape-mismatched. **Difficulty: blocked on evidence.**
- **Shape confound is unmitigated.** 42% of the estimate is evidence type.
  Options not yet explored: restricting the board to same-shape pairings as the
  primary view rather than a scenario, or a within-shape calibration that would
  have to be disclosed as a modelling convention. **Difficulty: hard, and it is
  a methodology decision rather than a coding one.**
- **Rater noise rests on one judge and two dossiers.** Codex hit 0% quota
  mid-run. Re-run with both families when it resets in ~5 days.
  **Difficulty: easy, blocked on quota.**
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
- ~~No CI.~~ Added 2026-09-14: `.github/workflows/tests.yml`, treating any
  non-zero exit as failure including pytest's 5.
- **No page-weight or export tooling**, because there is no site yet.
  **Difficulty: deferred until there is a board worth rendering.**
