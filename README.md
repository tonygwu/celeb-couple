# celeb-couple

Private. A research pipeline that asks whether two people in a romantic pairing
— on screen or in real life — were judged differently attractive **at the time
of that pairing**, using dated published judgments rather than photographs.

**Nothing here is published, deployed, or ranked.** The repository is private
and stays private. No image analysis, no facial or body analysis, no human
photo-rating: attractiveness estimates come from what magazines, polls and
awards actually said, on sources this project is permitted to use.

## Read these first

| Document | What it tells you |
|---|---|
| [`docs/THE-TRAP.md`](docs/THE-TRAP.md) | **Start here.** Why this design cannot produce a board with the available evidence |
| [`docs/M0-REPORT.md`](docs/M0-REPORT.md) | The pilot, end to end, every number generated from an artifact |
| [`docs/SCALING.md`](docs/SCALING.md) | Whether growing the roster helps. It does not, and by how much |
| [`docs/SOURCE-HUNT.md`](docs/SOURCE-HUNT.md) | Every source surface checked, and the negative result |
| [`docs/REACHABLE-PRODUCTS.md`](docs/REACHABLE-PRODUCTS.md) | What *can* be built with the evidence that exists |
| [`docs/GROUNDING-AUDIT.md`](docs/GROUNDING-AUDIT.md), [`docs/RELATIONSHIP-REVIEW.md`](docs/RELATIONSHIP-REVIEW.md) | **The two things only a person can do.** Load-bearing entries first in both |
| [`docs/CORRECTIONS.md`](docs/CORRECTIONS.md) | Every published number that moved, and why. **Read this if you read an earlier report** |
| [`docs/BACKLOG.md`](docs/BACKLOG.md), [`docs/BACKLOG-roster.md`](docs/BACKLOG-roster.md) | Known defects and scope not yet covered |
| [`AGENTS.md`](AGENTS.md) | How to run it, what spends quota, fleet git rules |

## Where it stands

The measurement works. The evidence does not support the product as specified.

- The rubric discriminates across a 29-point range on synthetic dossiers and
  produces ten distinct values.
- Two model families agree closely on the SYNTHETIC stress corpus. On the real
  dossiers only one family ran — codex reached 0% of its quota window mid-run —
  so cross-family agreement there is unmeasured. Repeat-scoring puts the
  least significant difference at about 2.56 points for rank-shaped estimates,
  over four dossiers repeated four times each. All four moved. The two award
  dossiers returned the same number eight times out of eight, which is still a
  sample too small to call zero, so no figure is quoted for that shape. Scoring
  the same dossier in two separate runs moved two of three estimates by 2.0
  points, which is what this noise floor predicts.
- Evidence **density** was the first bottleneck: every dossier once held exactly
  one observation, so the corpus produced 2 distinct values across a 5.5-point
  range. It now produces 12 across a range of 30.0
  (64.0–94.0), against the synthetic stress corpus's 29.
  The measurement apparatus is no longer the limiting factor.
- Evidence **shape** explains 31% of the estimate — omega-squared, the
  unbiased estimator. Earlier documents quoted 39%, which is eta-squared and
  biased upward by the five shape groups. An award pins near 92 by
  construction; ranked placements spread lower.
- **Coverage does not scale.** Going from 14 people to 100 gave 3.2x the
  observations and 8.5x the episodes, and left the count of comparable pairings
  at one.
- The source that would fix it — about a hundred ranked names a year — exists
  and is not reachable on any permitted route.

**The confound is aligned with gender.** Men in the corpus hold zero ranked
observations and women hold 17, so the male mean sits 3.65 points above the
female mean before any fact about any individual enters. In a product that
compares a man against a woman in every row, the sign of a typical gap is
decided by which sex somebody is rather than by what the judgments said.

**Every comparable pairing the project can produce is exactly 0.0, and every
non-zero gap is confounded by publication format.** That is structural, not a
shortage of data: a one-winner award is superlative by construction and so
concentrates on a single value, the award shape is the only one the free sources publish often enough to
match, and comparability requires matching shapes. So the pairings that qualify
as comparable are exactly the ones pinned at 92 on both sides.
[`docs/THE-TRAP.md`](docs/THE-TRAP.md) sets it out in full.

This is a working measurement apparatus and it is not a leaderboard.

## Running it

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest tests -q     # offline, deterministic, spends no quota
```

Plain `pip` works too, and is what CI uses — verified, since CI itself has never
been able to run:

```sh
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest tests -q
```

`data/` is gitignored: the corpus belongs in a separate private repository. Every
analysis script will tell you which command produces a missing artifact. See
`AGENTS.md` for the full chain order and which stages spend model quota.

## Working on this repo

Several agents work here at once, one per checkout, under the git protocol in
[AGENTS.md](AGENTS.md). Read that file first.

Checkouts live in `~/Code/misc/celebrity-couple/` as `repo-0` … `repo-3`. The
container directory is not itself a checkout.
