# Backlog

Filed by the overnight run of 2026-09-14. Difficulty tags are estimates.

See also `docs/BACKLOG-roster.md` for roster scope and the evidence-source hunt.

## Correctness and method

- **Deep-water miss in the romance classifier.** *Deep Water* (2022) came back
  `cannot_tell` for Affleck and de Armas, who play a married couple in it. The
  classifier is conservative by design, but 15 of 20 `cannot_tell` is a high
  rate and some are misses rather than genuine ambiguity. Worth sampling the
  plot texts to see whether the plot sections are too short or the rubric is too
  strict. **Difficulty: medium.**
- **`What Lies Beneath` classified `coerced_or_assault`.** Correct to exclude,
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

## Tooling

- **Smoke tests can clobber production artifacts.** Running
  `measure_rater_noise.py --repeats 1` as a formatting check overwrote the real
  4-repeat artifact. Scripts that write a default `--out` should refuse to
  overwrite a richer existing artifact, or smoke tests should always pass
  `--out`. **Difficulty: easy.**
- **No CI.** The suite is offline and deterministic and runs in well under a
  second, so there is no reason it could not gate. **Difficulty: easy.**
- **No page-weight or export tooling**, because there is no site yet.
  **Difficulty: deferred until there is a board worth rendering.**
