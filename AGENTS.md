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
.venv/bin/python -m pytest tests -q      # 134 tests, no model quota spent
```

The suite is offline and deterministic. **Treat any non-zero exit as failure,
including 5**, which pytest returns when it collects no tests at all. Never
write `pytest ...; echo $?` — the `;` reports the status of `echo`.

## The tools, and how to invoke them

Run every one from a clone root with `.venv/bin/python`. The first four are
read-only against Wikidata and Wikipedia. The last three spend model quota.

| Command | What it does | Spends quota |
|---|---|---|
| `scripts/fetch_records.py` | relationship candidates + birth dates for the cohort | no |
| `scripts/build_episodes.py` | merges progressions, flags defects, applies the adult window | no |
| `scripts/fetch_observations.py` | award observations from Wikipedia tables | no |
| `scripts/write_m0_report.py` | renders `docs/M0-REPORT.md` from the JSON artifacts | no |
| `scripts/run_stress.py --out data/pilot/stress` | the eight measurement stress cases | **yes** |
| `scripts/score_evidenced.py` | scores person-periods that have evidence | **yes** |
| `scripts/run_pilot.py` | bounded pairing selection and coverage | **yes** |

Quota rules for the three that spend:

- **Subscription only. API billing is asserted off at start-up** — a visible
  `ANTHROPIC_API_KEY` aborts the run.
- Judges are `fable` (Claude, via `claude -p`) and `astra` (via `codex exec`).
  **Gemini via `agy` does not work headlessly**: it reaches for a shell tool,
  headless mode auto-denies it, and the turn returns empty. Do not fix that by
  granting the permission — a judge with filesystem access is not isolated from
  the corpus it is being kept away from.
- Check `quotapick status` first. Fable headroom moves between accounts; on
  2026-09-14 only `~/.claude-e` had both 5-hour and weekly room.
- Every runner takes `--max-calls` style caps and **halts at the cap**, reporting
  the halt and the work it did not reach.

## What M0 measured

`docs/M0-REPORT.md`, generated from `data/pilot/`. Short version: the rubric
reads substance rather than counting documents, but the permitted sources
yielded 7 observations for 14 people, and award-shaped evidence compresses every
winner into a half-point band. Read it before proposing M1.

## New shared tooling

A new tool is not done until it is committed **and** registered in this file
with one line saying how other agents invoke it. An unregistered tool exists
for nobody.
