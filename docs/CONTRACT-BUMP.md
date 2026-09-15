# How to change a rubric or schema

Three filed items are waiting on this procedure, and it is easy to get wrong in
a way that is hard to see afterwards. Read it before editing anything under
`rubrics/`.

## Why a rubric edit is not a small change

The grading contract is `sha256(rubric bytes + schema bytes)`, truncated. Any
byte you change gives a new `contract_id`, and the plan is explicit that
estimates produced under different contract ids **must not be pooled** — scores
from different rubrics are not comparable and averaging them hides that.

So a one-line typo fix in `rubrics/standing/RUBRIC.md` costs a re-score of every
person-period, which is 39 model calls at present. That is the real price, and
it is why three trivial corrections are filed rather than applied.

## What was waiting, and landed together on 2026-09-14

All three were in [`docs/BACKLOG.md`](BACKLOG.md) with their reasoning. They are
struck through there now. Kept here because the next bump will look like this
one:

1. **`estimate.schema.json` nullable enums.** `missingness_reason` and `band`
   are declared nullable while their `enum` omits `null`, so every scored
   record would fail strict validation. Nothing validates today; a test fires
   if `jsonschema` is ever installed while this is unfixed.
2. **`contract_id` boundary ambiguity.** The parts are concatenated with no
   separator, so moving text from the end of the rubric to the start of the
   schema leaves the id unchanged. Length-prefix it.
3. **`MENTIONS.md` lists an undated example** that its own rule 3 says to skip.

Do them together. Each one alone costs the same re-score.

## The order

1. **Make every rubric and schema edit first.** All of them, in one commit.
   Bump `rubric_version` in the same commit — `standing-rubric-2.0` becomes
   `2.1`. A changed contract with an unchanged version string is the worst
   outcome, because the artifacts then disagree about which rubric they used.

2. **Record the old contract id** before anything overwrites it:

   ```sh
   .venv/bin/python -c "import json;print(json.load(open('data/pilot/run/evidenced_scores.json'))['contract']['contract_id'])"
   ```

3. **Archive the existing scores.** `score_evidenced.py` does this
   automatically now, into `data/pilot/run/history/`, content-addressed. Check
   the file lands: the old estimates are the only record of what the previous
   contract produced, and they are what makes a before-and-after comparison
   possible at all.

4. **Re-score.** Use both judge families if codex quota allows — this is the
   right moment, because a re-score is happening anyway:

   ```sh
   quotapick status                       # pick an account with fable headroom
   .venv/bin/python scripts/score_evidenced.py --judges fable,astra \
       --account <config dir> --max-calls 60
   ```

5. **Re-score the rest, in this order.** The order matters: `run_stress.py`
   reads the rater-noise floor from `measure_rater_noise.py`'s artifact and
   refuses a stale one, so running it first wastes about 27 calls on a run that
   cannot finish. It refuses before spending anything, but only if the artifact
   is already stale rather than being made stale later.

   ```sh
   .venv/bin/python scripts/measure_rater_noise.py --account <config dir>
   .venv/bin/python scripts/run_stress.py --out data/pilot/stress \
       --fable-account <config dir>
   .venv/bin/python scripts/score_roster_joint.py --account <config dir>
   ```

6. **Re-run the chain and check what moved.**

   ```sh
   bash scripts/run_chain.sh reports
   .venv/bin/python scripts/cross_run_stability.py \
       --b-scores data/pilot/run/history/evidenced_scores-<hash>.json \
       --b-name old-contract
   ```

   That last command will REFUSE, because the contracts differ — which is
   correct and is the point. A difference across a contract boundary is a
   difference between rubrics, not run-to-run variance, and the script exists
   to stop that being read as noise. Compare the estimates by hand instead, and
   say in the commit which ones moved and by how much.

7. **Update [`docs/CORRECTIONS.md`](CORRECTIONS.md)** with any published number
   that changed, and why.

## What the 2026-09-14 bump taught, which this procedure did not say

The first real bump found four things the steps above got wrong or omitted.

1. **The blast radius is every rubric, not the one you edited.** Fixing the
   `contract_id` boundary changed the HASHING SCHEME, so all three ids moved --
   standing, mentions and romance -- even though romance's bytes never changed.
   The re-score was therefore not 39 calls. It was prose mentions (cohort and
   partners), romance classification, evidenced scores for two judge families,
   the roster-scale joint scores, rater noise and the stress corpus. Budget for
   the full set before starting, not for the rubric you happened to open.

2. **A scheme change is not a version bump.** "Do not bump the version without
   changing the bytes" is still right, so romance stayed at `romance-1.0` while
   its id moved. That combination is indistinguishable from a mistake unless
   something records it, so `contract_id_scheme` is now stamped beside the id in
   every artifact.

3. **Two scripts did not honour the guard**, and one of them was the report
   renderer. `run_chain.sh` records a stage failure and continues by design, so
   the chain refused at every `require()`-based stage and then rendered
   `docs/M0-REPORT.md` from the stale corpus anyway. The chain now refuses the
   whole report pass up front when any artifact is stale. Check the preflight
   fires before trusting a bump: `bash scripts/run_chain.sh reports` must exit 1
   and name every stale artifact.

4. **Expect a CLUSTER of failures, not one, and sort them into two piles.**
   The first draft of this note said "exactly one place". That was written after
   editing only the rubric files; once the corpus was re-fetched the count was
   nine. Two piles:

   *Expected while the corpus is stale* — they clear when the re-score lands:

   - `test_stale_contract.py` (both tests)
   - `test_doc_claims.py`, `test_doc_numbers.py`, `test_report_prose.py`, which
     regenerate or audit documents the guard now refuses to build

   *Real, and the bump surfaced them* — they need fixing:

   - `test_observation_verification.py` asserted the literal `41`. The corpus
     legitimately grew to 42 on a full pass, so a hand-typed number in a TEST
     went stale and lied, which is the defect `audit_doc_numbers.py` exists to
     catch in prose. It asserts `verified == checked` now, plus `checked > 0` so
     an empty corpus cannot pass vacuously.
   - `test_rater_noise_summary.py` built a fixture stamped `contract_id: "test"`,
     which the new `--recompute` guard correctly refuses. The fixture now derives
     the current id instead of pinning one.

   If a failure is in neither pile, something beyond the contract moved.

   **The failing SET moves as stages land, and the count can stay the same
   while the membership changes.** Measured on this bump: nine before the
   re-score, nine after it, but not the same nine. The checkpoint-contract test
   cleared and two document tests appeared, because regenerating a report is
   what exercises them. Compare the NAMES between runs, not the count -- a
   steady total reads like no progress and is not.

## What you must not do

- **Do not pool.** Estimates from the old and new contracts do not average.
  `refuse_mixed_contracts` exists for this and is deliberately not wired in: on
  the record shape this pipeline writes, no row carries a per-record
  `contract_id`, so the guard would pass on genuinely mixed input and read as
  provenance that had been checked. See the closed W072 entry in
  `docs/BACKLOG.md`. The discipline is yours, and `refuse_stale_contract` inside
  `require()` is what actually catches a bump.
- **Do not edit a rubric and skip the re-score.** The artifacts would then
  record a contract id for bytes the judge never saw.
- **Do not bump the version without changing the bytes,** or the reverse.
