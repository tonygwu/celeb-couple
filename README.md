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
| [`docs/BACKLOG.md`](docs/BACKLOG.md), [`docs/BACKLOG-roster.md`](docs/BACKLOG-roster.md) | Known defects and scope not yet covered |
| [`AGENTS.md`](AGENTS.md) | How to run it, what spends quota, fleet git rules |

## Where it stands

The measurement works. The evidence does not support the product as specified.

- The rubric discriminates across a 29-point range on synthetic dossiers and
  produces ten distinct values.
- Two model families agree closely on real dossiers, and repeat-scoring puts the
  least significant difference at about 1.2 points.
- Evidence **density** was the first bottleneck: every dossier once held exactly
  one observation, so the corpus produced 2 distinct values across a 5.5-point
  range. It now produces 10 across a range of 27.0
  (66.0–93.0), against the synthetic stress corpus's 29.
  The measurement apparatus is no longer the limiting factor.
- Evidence **shape** explains 46% of the estimate. An award pins near 92 by
  construction; ranked placements spread lower.
- **Coverage does not scale.** Going from 14 people to 100 gave 3.7x the
  observations and left the count of comparable pairings at one.
- The source that would fix it — about a hundred ranked names a year — exists
  and is not reachable on any permitted route.

**The confound is aligned with gender.** Men in the corpus hold zero ranked
observations and women hold twelve, so the male mean sits 3.65 points above the
female mean before any fact about any individual enters. In a product that
compares a man against a woman in every row, the sign of a typical gap is
decided by which sex somebody is rather than by what the judgments said.

**Every comparable pairing the project can produce is exactly 0.0, and every
non-zero gap is confounded by publication format.** That is structural, not a
shortage of data: a one-winner award is superlative by construction and pins at
92, the award shape is the only one the free sources publish often enough to
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

`data/` is gitignored: the corpus belongs in a separate private repository. Every
analysis script will tell you which command produces a missing artifact. See
`AGENTS.md` for the full chain order and which stages spend model quota.

## Working on this repo

Several agents work here at once, one per checkout, under the git protocol in
[AGENTS.md](AGENTS.md). Read that file first.

Checkouts live in `~/Code/misc/celebrity-couple/` as `repo-0` … `repo-3`. The
container directory is not itself a checkout.
