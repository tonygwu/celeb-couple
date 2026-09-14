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

## What is waiting

All three are in [`docs/BACKLOG.md`](BACKLOG.md) with their reasoning:

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
       --account <config dir> --max-calls 120
   ```

5. **Re-run the chain and check what moved.**

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

6. **Update [`docs/CORRECTIONS.md`](CORRECTIONS.md)** with any published number
   that changed, and why.

## What you must not do

- **Do not pool.** Estimates from the old and new contracts do not average.
  `refuse_mixed_contracts` exists for this and currently has no caller, so the
  discipline is yours.
- **Do not edit a rubric and skip the re-score.** The artifacts would then
  record a contract id for bytes the judge never saw.
- **Do not bump the version without changing the bytes,** or the reverse.
