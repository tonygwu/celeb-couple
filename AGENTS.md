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

## New shared tooling

A new tool is not done until it is committed **and** registered in this file
with one line saying how other agents invoke it. An unregistered tool exists
for nobody.
