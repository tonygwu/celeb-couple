# Notes for coding agents working in this repo

Several agents work this repository at the same time, one agent per checkout.
Git is the only channel between them. Read this file before your first git
command.

## Checkout layout on this machine

`~/Code/misc/celebrity-couple/` is a **container**, not a checkout. It holds
several checkouts of this same repository:

| Checkout | Role |
|---|---|
| `repo-0` | Working checkout for agent sessions. Edit here. |
| `repo-1` | Working checkout for agent sessions. Edit here. |
| `repo-2` | Working checkout for agent sessions. Edit here. |
| `repo-3` | Working checkout for agent sessions. Edit here. |

There is no deploy or install checkout yet. If this project ever gains one,
add a `repo-prod` checkout, give it the deploy-only role, and record that role
in this table in the same commit. A role that lives only in an agent's memory
does not exist.

Your checkout name is your **handle**. Use it when you claim work.

## The rules

1. **Sync before you touch.** `git fetch && git rebase` before you read or
   edit. Your local HEAD is a hypothesis about the repo, not a fact. A session
   that resumes after idle time re-fetches before its *first* git command, not
   before its first push.

2. **Push every completed unit, immediately.** Never end a turn with a
   publishable change sitting unpushed. If something blocks the push, say what
   it is. A held commit and a hung agent look identical from outside.

3. **Stage by name, never by sweep.** `git add -A` and `git add .` are
   forbidden here. Untracked files you did not create are another agent's work
   in progress. A tree dirty with foreign files is normal, not a mess to tidy.

4. **Claim before you work.** Push the claim before you start. Add
   `[claimed by: repo-N]` to the item's line, commit that file by name, push.
   If the claim push is rejected, another agent won the item. Fetch and pick
   another.

5. **Divergence is a blocker.** More than 5 commits ahead, or any commits
   behind for more than a day, gets surfaced to the operator. Never let it
   accumulate quietly.

6. **Committed code must run from any checkout.** Never write a
   checkout-absolute path into committed code. Derive the repo root at
   runtime: `git rev-parse --show-toplevel`, or `Path(__file__).resolve()` in
   Python. A hardcoded path is correct in one checkout and wrong in three.

7. **A refusing hook is another agent talking to you.** Read its text and the
   sentinel file it names. Never `--no-verify`, never delete the hook.

8. **History rewrites: stop, fetch, reconcile.** Unknown SHAs or a
   non-fast-forward rejection mean the remote history may have moved under
   you. Stop, fetch, and reconcile against the coordinator notice at the top
   of this file. Never force-push over `main`.

9. **One session, one terminal.** Never resume the same session id from two
   checkouts at once. Concurrent appends corrupt the transcript.

## Git identity

Every checkout is configured with the GitHub noreply author address:

```sh
git config user.email 446441+tonygwu@users.noreply.github.com
```

This is set so the history never needs an author rewrite if the repository is
made public later.

## Setup, in a fresh clone

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest tests -q      # offline; spends no model quota
```

**CI does not run.** `.github/workflows/tests.yml` exists, but all 30 of its
runs have been refused at GitHub's billing gate before reaching pytest, so the
repository's Actions state is red while the suite is green. Do not read a green
Actions badge as verification and do not read a red one as a test failure. Run
the suite locally; that is the only gate that has ever executed. See
`docs/BACKLOG.md`.

The suite is offline and deterministic. The count is deliberately not written
down here: a hand-typed number goes stale and then lies, which is the defect
this project's sibling repo paid for five separate times. Run it and read it. **Treat any non-zero exit as failure,
including 5**, which pytest returns when it collects no tests at all. Never
write `pytest ...; echo $?` — the `;` reports the status of `echo`.

## The tools, and how to invoke them

Run every one from a clone root with `.venv/bin/python`. The first four are
read-only against Wikidata and Wikipedia. The last three spend model quota.

| Command | What it does | Spends quota |
|---|---|---|
| `scripts/fetch_records.py` | relationship candidates + birth dates for the cohort | no |
| `scripts/build_episodes.py` | merges progressions, flags defects, applies the adult window | no |
| `scripts/build_partner_universe.py` | derives the outside-roster partners from scorable episodes | no |
| `scripts/fetch_onscreen_candidates.py` | films where a male and a female roster member co-star | no |
| `scripts/resolve_roster.py` | turns a name list into a roster file with Wikidata ids | no |
| `scripts/scaling_report.py` | pilot vs full roster; does coverage scale | no |
| `scripts/source_requirement.py` | how deep a source would have to be | no |
| `scripts/reachable_products.py` | what can be built with the evidence that exists | no |
| `scripts/fetch_observations.py` | list/award observations from Wikipedia tables, for cohort **and** partners | no |
| `scripts/merge_prose_mentions.py` | folds prose mentions in, deduping on person+year+publisher | no |
| `scripts/joint_coverage.py` | are BOTH sides scorable in the same period, and is the pairing comparable | no |
| `scripts/evidence_density.py` | observations per person-period — the actual bottleneck | no |
| `scripts/alignment_gap.py` | what the nearby-period bound costs, per pairing | no |
| `scripts/partner_eligibility.py` | splits "no evidence found" from "never rate" | no |
| `scripts/shape_confound.py` | how much of the estimate is evidence format | no |
| `scripts/offset_diagnostic.py` | cross-gender offset sensitivity; exits non-zero if the identity breaks | no |
| `scripts/grounding_audit.py` | automated grounding checks + the human review sheet | no |
| `scripts/write_m0_report.py` | renders `docs/M0-REPORT.md` from the JSON artifacts | no |
| `scripts/relationship_review.py` | the human review sheet for relationship claims, load-bearing ones first | no |
| `scripts/verify_trap.py` | re-derive THE-TRAP.md's three structural claims; exits 1 if any stopped holding | no |
| `scripts/cross_run_stability.py` | do two separate runs score an identical dossier the same | no |

A re-score does not destroy the previous estimates any more: `score_evidenced.py`
archives both score artifacts under `data/pilot/run/history/` before overwriting,
content-addressed so an unchanged re-run does not pile up copies. To compare two
runs of the same corpus, point `cross_run_stability.py --b-scores` at a history
file. Run-to-run variance is real — two of three identical dossiers moved by
2.0 points — so both runs have to survive for it to be measurable.
| `scripts/audit_doc_numbers.py` | cross-checks measured numbers typed into any tracked Markdown against the artifacts; exits 1 on a stale one | no |
| `scripts/run_stress.py --out data/pilot/stress` | the eight measurement stress cases | **yes** |
| `scripts/score_evidenced.py` | scores person-periods that have evidence | **yes** |
| `scripts/classify_romance.py` | is a co-starring pair actually a romance in the film | **yes** |
| `scripts/extract_prose_mentions.py` | list memberships from biographical prose | **yes** |
| `scripts/measure_rater_noise.py` | repeat-scores unchanged dossiers | **yes** |
| `scripts/run_pilot.py` | bounded pairing selection and coverage | **yes** |
| `scripts/score_roster_joint.py` | scores only what the roster-scale joint pairings need | **yes** |

The quota-spending scripts take `CELEB_JUDGES` (default `fable,astra`) and
`CELEB_MAX_CALLS`, or equivalent flags. Run the whole chain in this order after
changing any source: `fetch_records` → `build_episodes` → `build_partner_universe` →
`fetch_observations` → `merge_prose_mentions` (once per
mentions file) → `score_evidenced` → `joint_coverage` → `evidence_density` →
`alignment_gap` → `shape_confound` → `grounding_audit` → `offset_diagnostic` →
`relationship_review` → `verify_trap` → `cross_run_stability` →
`write_m0_report` → `audit_doc_numbers`.

Run the free stages and the reports with the chain script, which encodes the
dependency order so a stage cannot run before the one it needs:

```sh
bash scripts/run_chain.sh free      # no model calls
bash scripts/run_chain.sh reports   # regenerate every report from artifacts
bash scripts/run_chain.sh all
```

The quota-spending stages are deliberately NOT in it. They need an account and a
cap chosen by a human who has looked at `quotapick status`.

Quota rules for the ones that spend:

- **Subscription only. API billing is asserted off at start-up** — a visible
  `ANTHROPIC_API_KEY` aborts the run.
- Judges are `fable` (Claude, via `claude -p`) and `astra` (via `codex exec`).
  **Gemini via `agy` does not work headlessly**: it reaches for a shell tool,
  headless mode auto-denies it, and the turn returns empty. Do not fix that by
  granting the permission — a judge with filesystem access is not isolated from
  the corpus it is being kept away from.
- Check `quotapick status` first, and pass what it tells you. **There is no
  default account**: every paid script takes `--account <config dir>` or reads
  `CELEB_ACCOUNT`, and refuses to start without one, naming the config dirs it
  can see. The six scripts used to default to `~/.claude-e`, which on
  2026-09-14 was at 0% on its 5-hour window while `~/.claude-c` had 66% fable
  headroom — a default that is wrong is worse than no default, because the run
  fails as `auth_or_quota` and reads like a broken judge. A `--dry-run` needs
  no account; resolution happens where the judge is built.
- Every runner takes `--max-calls` style caps and **halts at the cap**, reporting
  the halt and the work it did not reach.

## Running the roster-scale chain

The pilot chain defaults to `data/pilot/`. The 100-name roster uses the same
scripts with different paths:

```sh
.venv/bin/python scripts/fetch_records.py       --cohort docs/roster-100.json --out data/roster100/records
.venv/bin/python scripts/build_episodes.py      --records data/roster100/records/relationship_candidates.json \
                                                --cohort docs/roster-100.json --out data/roster100/records/episodes.json
.venv/bin/python scripts/build_partner_universe.py --episodes data/roster100/records/episodes.json \
                                                --cohort docs/roster-100.json --out data/roster100/records/partner_universe.json
.venv/bin/python scripts/fetch_observations.py  --cohort docs/roster-100.json \
                                                --partners data/roster100/records/partner_universe.json \
                                                --out data/roster100/observations
```

Everything above is free. `scripts/score_roster_joint.py` then scores only the
dossiers the jointly covered pairings need, which is about nine rather than the
127 a full pass would cost.

## What has been measured

`docs/M0-REPORT.md`, generated from `data/pilot/`. Read it before proposing
anything. The findings that should shape any next step:

1. **The rubric is not the problem.** On synthetic dossiers it spans 63 to 92
   and produces ten distinct values.
2. **Evidence density was the bottleneck.** Every real dossier once carried
   exactly one observation, so the corpus produced two distinct values. Adding
   prose mentions took it to twelve.
3. **Evidence SHAPE explains 39% of the estimate.** An editorial award pins
   near 92 by construction; ranked placements spread lower. Three of four
   jointly covered pairings pit one against the other, so their gaps are
   substantially about publication format.
4. **The one comparable gap is 0.0**, against a least significant difference of
   about 2.22 points for rank-shaped estimates, measured on four dossiers
   repeated four times each. There is no leaderboard here yet, and adding more
   award-shaped sources will not create one. The LSD is quoted PER SHAPE:
   pooling the award dossiers' zero measured variance with the ranked ones'
   halved it to 1.2, which several documents published. Every one of the four
   ranked dossiers moved between repeats; both award dossiers returned the
   same number eight times out of eight.

5. **The shape effect is confirmed under controlled conditions.** Stress case
   S2 renders ONE substantive judgment as an award, as a ranked placement and
   as prose. The estimates spread 4 points — above the 2.22 floor — so format
   moves the number with the substance held identical by construction. That is
   an independent route to finding 3, and it is the strongest form of the
   argument because nothing about the person varies.
6. **Every real estimate came from ONE judge family.** The plan decided J = 2
   so a one-family idiosyncrasy could be told from a property of the rubric.
   Codex reached 0% of its 7-day window mid-run, so all 39 person-periods were
   scored by `fable` alone and the `astra` column in the report is empty for
   that reason, not because the judges agreed. Both families DID run on the
   stress corpus. Re-scoring with codex when its quota returns is the single
   cheapest thing that would strengthen every conclusion above.

Do not treat a bigger confounded number as progress over a smaller comparable
one.

## New shared tooling

A new tool is not done until it is committed **and** registered in this file
with one line saying how other agents invoke it. An unregistered tool exists
for nobody.
