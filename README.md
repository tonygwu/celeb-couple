# celeb-couple

A research pipeline that asks whether two people in a romantic pairing — on
screen or in real life — were judged differently attractive **at the time of
that pairing**, using dated published judgments rather than photographs.

It did not work, and the interesting part is why. The measurement apparatus is
sound and the evidence cannot support the product it was built for. That
negative result, and the machinery that establishes it, is what this repository
is for.

---

## Read this before you read any number here

This project scores how attractive real, named people were judged to be. If you
take one thing from this README, take this section.

**These are model judgments, not measurements.** A large language model is asked
how conventionally attractive a person was perceived to be in a given year, and
it answers on a 0–100 scale against a written rubric. Nothing here measures
anybody's appearance. The output is a record of what a model says, and it should
be read as evidence about the model at least as much as evidence about the
person.

**Most scores rest on no published evidence at all.** Of the 2833 person-years
in `data/roster100/run/person_gradings.json`, **134 — 4.7% — cite a dated
published observation.** The other 2699 were produced by a judge working from
its own prior knowledge with no source supplied. The scoring prompt says so in
as many words:

> **None supplied.** That is the normal case and is not evidence of a low score.
> Judge from what you know and set `evidence_used` to false.

Recompute that figure rather than trusting this paragraph:

```sh
.venv/bin/python -c "
import json
d = json.load(open('data/roster100/run/person_gradings.json'))['canonical']
ev = sum(1 for v in d.values() if v['any_evidence'])
print(ev, 'of', len(d), '= %.1f%%' % (100 * ev / len(d)))"
```

`docs/BOARDS.md` carries the same warning about itself, in its own first lines:
*"These are subjective model judgments, not measurements. No source backs any
number here."*

**No image is ever fetched, attached, or shown to any model.** There is no face
analysis, no body analysis, and no photo rating. A judge works from what it
already knows about a public figure. `tests/test_no_age_formula.py` pins this
over both the live and the superseded scoring paths, and bans image transport —
fetching, encoding, or passing an image url — rather than banning the word,
because the rubric legitimately tells the judge to weigh coverage it already
knows about.

**No age arithmetic exists anywhere in the scoring path.** If an estimate falls
as somebody ages, that is the judge's own per-pairing assessment. It is never a
curve applied by code, which would manufacture the project's largest gaps out of
arithmetic rather than judgment. Same test file.

### The known confounds, stated plainly

These are not caveats discovered by a critic. The project measured them on
itself, and they are the reason it reports a negative result.

1. **Evidence shape explains 40% of the estimate** (omega-squared, the unbiased
   estimator; the biased eta-squared that earlier documents quoted reads 39%).
   A one-winner editorial award pins near 92 by construction. A ranked placement
   spreads lower. So a gap between two people can be substantially about the
   format their coverage happened to be published in.

2. **That confound is aligned with gender, which is the most consequential
   finding here.** Men in the corpus hold zero ranked observations and women hold
   17, so the male mean sits 4.23 points above the female mean before any fact
   about any individual enters. In a product that compares a man against a woman
   in every row, the sign of a typical gap is decided by which sex somebody is
   rather than by what the judgments said. Removing any single man moves that
   offset between 2.9 and 5.3 and never reverses it, so it is not one person
   carrying it.

3. **Every comparable gap the project can produce is exactly 0.0**, and every
   non-zero gap is shape-mismatched. That is structural rather than a shortage
   of data. `docs/THE-TRAP.md` sets out the argument and `scripts/verify_trap.py`
   re-derives it, exiting non-zero if it ever stops holding.

4. **The judges are noisy and the noise is not pinned.** Repeat-scoring puts the
   least significant difference at about 1.03 points for rank-shaped estimates,
   over four dossiers repeated four times each. All four moved between repeats.
   The same judge on the same four dossiers measured a least significant
   difference of 2.56 on one run and 1.03 on the next, so quote the interval and
   not the point.

5. **Ranking named people is the risk this design carries.** The boards in
   `docs/BOARDS.md` rank real people, and some of the partners named there are
   private individuals known publicly only as somebody's former partner. Nothing
   about a person's private life is inferred, and every relationship claim is
   sourced to Wikidata or Wikipedia in `docs/RELATIONSHIP-REVIEW.md`. The
   attractiveness numbers beside them are still model opinion with no source
   behind them, and they are published here as a research artifact rather than
   as a claim about anyone.

**Nobody is removed from the roster by name.** The 100 people were chosen on
prominence *before* anything was scored, deliberately, so that the roster could
not be tuned to the result. Two mechanical rules decide who is ranked: only
films from 1980 on are graded, and a person needs three scored romances. Both
rules print how many people they hide, because a threshold nobody can see is the
same problem as a silent exclusion.

---

## What it actually does

```
Wikidata + Wikipedia + local IMDb dumps
        │
        ├─ who partnered whom, and when          records / episodes
        ├─ who co-starred with whom, and when    on-screen candidates
        ├─ which co-star pairs are a romance     LLM, cached per film
        │
        ├─ dated published observations          awards, ranked lists, prose
        │                                        on permitted sources only
        │
        └─ judge each (person, year) ONCE        LLM, film-blind, cached
                 │
                 └─ a pairing gap is a SUBTRACTION of two cached scores
                          │
                          └─ four leaderboards + a within-sex normalized view
```

Two design decisions are worth knowing before reading the code.

**A person-year is judged once, film-blind.** An earlier version judged each
pairing and told the judge which film it was scoring, and the same person in the
same year came back 9.0 for one film and 9.5 for another. Scoring the person
rather than the pairing removed that, and it made gaps free: an already-judged
pair costs nothing to re-derive.

**Every grading is kept and the canonical score is their mean.** The artifact
carries `n`, `spread` and the models behind each score, so 18 person-years
resting on one grading are not silently treated as equal in precision to those
resting on four. An unjudged grading is a refusal and not a zero; averaging a
refusal in as 0.0 would drag a person to the bottom of the board.

## What it found

The measurement works. The evidence does not support the product as specified.

- The rubric discriminates across a 29-point range on synthetic dossiers and
  produces ten distinct values. The rubric was never the problem.
- Evidence **density** was the first bottleneck: every dossier once held exactly
  one observation, so the corpus produced 2 distinct values across a 5.5-point
  range. It now produces 17 across a range of 30.0
  (64.0–94.0), against the synthetic stress corpus's 29.
  The measurement apparatus is no longer the limiting factor.
- Evidence **shape** explains 40% of the estimate — omega-squared, the
  unbiased estimator. Earlier documents quoted 39%, which is eta-squared and
  biased upward by the five shape groups. An award pins near 92 by
  construction; ranked placements spread lower.
- **Coverage does not scale.** Going from 14 people to 100 gave 3.2x the
  observations and 8.8x the episodes, and left the count of comparable pairings
  at one.
- The source that would fix it — about a hundred ranked names a year — exists
  and is not reachable on any permitted route.
- Two model families agree closely on the SYNTHETIC stress corpus. On the real
  dossiers only one family ran — codex reached 0% of its quota window mid-run —
  so cross-family agreement there is unmeasured.

**Every one of those findings has been sensitivity-tested.** The structural
claims hold at nine of ten settings of the nearby-period bound and the romance
filter, failing only with both dials at their loosest. The noise floor moves
between 2.35 and 2.89 when any single repeated dossier is dropped, and no
verdict flips across that range. The gender offset moves between 2.9 and 5.3
when any single man is removed entirely, and never reverses. The source
requirement converges on the same answer under three different popularity
weightings. None of the conclusions rests on one choice, one dossier, or one
person.

This is a working measurement apparatus and it is not a leaderboard.

## Running it

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m pytest tests -q     # offline, deterministic, spends no quota
```

Plain `pip` works too, and is what CI uses:

```sh
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest tests -q
```

The suite is offline and deterministic: it makes no network call and spends no
model quota. Every judge is faked. **Treat any non-zero exit as failure,
including 5**, which pytest returns when it collects no tests at all.

The free analysis chain runs from committed artifacts and needs no model:

```sh
bash scripts/run_chain.sh free      # no model calls
bash scripts/run_chain.sh reports   # regenerate every report from artifacts
```

`AGENTS.md` has the full tool table, the chain order, and which stages spend
model quota.

### What it costs

Three dependencies, all pure Python: `pytest`, `hypothesis`, `jsonschema`. No
numpy, no scipy. Exact arithmetic uses `fractions.Fraction` from the standard
library.

Everything except the judging is free. The Wikidata and Wikipedia fetchers make
ordinary anonymous HTTP requests. Reproducing the scored corpus is the only part
that costs anything, and `data/roster100/run/person_gradings.json` records what
it took:

| Model | Gradings |
|---|---|
| `claude-opus-5` | 2812 |
| `claude-fable-5-1` | 220 |
| `gpt-6-astra` | 215 |
| `claude-sonnet-5` | 4 |
| **total** | **3251** |

That is 3251 judge calls for 2833 person-years covering 1429 people between 1953
and 2026, plus the romance-classification calls that decide which co-starring
pairs are couples at all. Those calls were made through subscription CLIs rather
than a metered API, so the cost was quota and wall-clock rather than a bill. If
you reproduce this against a metered API, price 3251 single-turn calls with a
prompt of a rubric plus a short dossier, and budget for the romance pass on top.

**Re-running the judging is not necessary to reproduce the analysis.** The
scores are cached, gaps are derived by subtraction, and `scripts/rebuild_boards.py`
rebuilds every board from the cache for free.

Every quota-spending script refuses to start without an explicit account, takes
a `--max-calls` cap, halts at that cap, and reports the work it did not reach.
API billing is asserted off at start-up: a visible `ANTHROPIC_API_KEY` aborts the
run.

## Where the data comes from

`data/` is **not** in this repository and never has been. It holds the corpus
and is gitignored, so a fresh clone carries the code, the rubrics, the rosters
and the generated reports, and none of the scored artifacts. Analysis scripts
name the command that produces a missing artifact, and tests that need the
corpus skip cleanly without it.

Sources are Wikidata, Wikipedia, and local IMDb bulk dumps.

**The IMDb `.tsv.gz` dumps are never committed.** They are about 2 GB and not
ours to redistribute. `scripts/build_imdb_graph.py` reads them from `--dumps` or
`CELEB_IMDB_DIR`, outside the repository. `.gitignore` blocks `*.tsv` and
`*.tsv.gz`, and no such file has ever been committed.

Four publishers are excluded by policy from every route, archives included:
People Inc. / people.com, Ziff Davis / askmen.com, Maxim, and Condé Nast /
Glamour. `docs/SOURCE-HUNT.md` records every source surface checked and the
negative result.

## The documents

| Document | What it tells you |
|---|---|
| [`docs/THE-TRAP.md`](docs/THE-TRAP.md) | **Start here.** Why this design cannot produce a board with the available evidence |
| [`docs/M0-REPORT.md`](docs/M0-REPORT.md) | The pilot, end to end, every number generated from an artifact |
| [`docs/SCALING.md`](docs/SCALING.md) | Whether growing the roster helps. It does not, and by how much |
| [`docs/SOURCE-HUNT.md`](docs/SOURCE-HUNT.md) | Every source surface checked, and the negative result |
| [`docs/REACHABLE-PRODUCTS.md`](docs/REACHABLE-PRODUCTS.md) | What *can* be built with the evidence that exists |
| [`docs/BOARDS.md`](docs/BOARDS.md) | The four leaderboards. Read the warning in its first lines |
| [`docs/GROUNDING-AUDIT.md`](docs/GROUNDING-AUDIT.md), [`docs/RELATIONSHIP-REVIEW.md`](docs/RELATIONSHIP-REVIEW.md) | **The two things only a person can do.** Load-bearing entries first in both |
| [`docs/CORRECTIONS.md`](docs/CORRECTIONS.md) | Every published number that moved, and why |
| [`docs/CONTRACT-BUMP.md`](docs/CONTRACT-BUMP.md) | Why editing a rubric costs a full re-score |
| [`docs/PLAN-v4.md`](docs/PLAN-v4.md) | The current design and the reasoning behind it |
| [`docs/BACKLOG.md`](docs/BACKLOG.md), [`docs/BACKLOG-roster.md`](docs/BACKLOG-roster.md) | Known defects and scope not yet covered |
| [`AGENTS.md`](AGENTS.md) | How to run it, what spends quota, and the conventions this repository holds itself to |

Several of those documents are generated from artifacts rather than written by
hand. `scripts/audit_doc_numbers.py` cross-checks measured numbers typed into
any tracked Markdown file against the artifacts they came from and exits 1 on a
stale one, which is why the figures in this README are safe to quote.

## How this repository works

`AGENTS.md` is the contributor guide, and it is long because most of it is
incident history: a defect, what it cost, and the check that now prevents it.
The conventions that matter to an outside reader are short.

- **Committed code must run from any checkout, any machine, any environment.**
  Derive the repo root at runtime. A hardcoded path is correct in one checkout
  and wrong in every other.
- **Read pytest's own exit status, not something downstream of it.**
  `pytest tests -q; echo $?` reports the status of `echo`, and a pipe reports
  the status of the last command in it. Both have pushed a red suite here.
- **Do not edit anything under `rubrics/` without reading
  [`docs/CONTRACT-BUMP.md`](docs/CONTRACT-BUMP.md).** The grading contract is a
  hash of the rubric and schema, so a one-line typo fix gives a new
  `contract_id` and invalidates every estimate made under the old one. A trivial
  edit costs a full re-score.
- **A number in a document must come from an artifact.** If you state one, say
  which artifact it came from, and expect `scripts/audit_doc_numbers.py` to
  check it.

## Status and licence

This is a completed research pilot published for its negative result. It is not
a product, it is not deployed, and there is no ranking anybody is invited to
take seriously.

**MIT.** See [`LICENSE`](LICENSE). The licence covers the code in this
repository. It says nothing about the scored corpus under `data/`, which is
gitignored and not distributed here, and nothing about the third-party sources
the pipeline reads.
