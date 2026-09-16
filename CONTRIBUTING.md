# Contributing

Thanks for looking. Read [`README.md`](README.md) first, especially the section
headed *"Read this before you read any number here"*. This project scores how
attractive real, named people were judged to be, by language models, and the
framing in that section is not decoration.

`AGENTS.md` is the full contributor guide. It is long, and most of it is written
for coding agents working several checkouts of this repository at once. This
file is the short version for a human sending a pull request.

## Setting up

```sh
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest tests -q
```

Three dependencies, all pure Python. The suite is offline and deterministic: it
makes no network call, spends no model quota, and fakes every judge. It runs in
about 13 seconds.

`data/` is gitignored and holds the scored corpus, so a fresh clone does not
have it. That is expected. Tests that need the corpus skip cleanly without it,
and analysis scripts name the command that produces a missing artifact.

## What a change needs

**A failing-then-passing test.** A fix without one is not a fix. If the bug is
in a guard, mutate the thing it guards and show the guard fires.

**Read pytest's own exit status, not something downstream of it.** Both of these
report the wrong command's status and have pushed a red suite here:

```sh
pytest tests -q; echo $?              # the status of echo
pytest tests -q | tail -2             # the status of tail
```

Use this instead, and treat **any** non-zero exit as failure, including 5, which
pytest returns when it collects no tests at all:

```sh
.venv/bin/python -m pytest tests -q > /dev/null 2>&1; RC=$?
```

**No checkout-absolute or home-absolute paths in committed code.** Derive the
repo root at runtime with `Path(__file__).resolve()`. Use `sys.executable`, not
`.venv/bin/python`, when a test spawns an interpreter: CI installs with
setup-python and has no `.venv`.

**Every number in a document must come from an artifact.** Say which artifact.
`scripts/audit_doc_numbers.py` cross-checks measured numbers typed into any
tracked Markdown file and exits 1 on a stale one, so run it if you touch a doc.

**Fail loudly.** A missing key raises rather than defaulting to zero or empty.
Any cap, truncation or sampling is reported along with what it cut. A
permissive parser turns a loud failure into a quiet wrong answer, and this
repository has paid for that several times over — `docs/BACKLOG.md` opens with
the defect class.

## Things that need more than a pull request

**Do not edit anything under `rubrics/` without reading
[`docs/CONTRACT-BUMP.md`](docs/CONTRACT-BUMP.md).** The grading contract is a
hash of the rubric and its schema, so a one-line typo fix produces a new
`contract_id`, and estimates made under different ids must never be pooled. A
trivial edit therefore costs a full re-score of every affected artifact. Open an
issue first.

**Do not add a source without checking the policy.** Four publishers are
excluded from every route, archives included: People Inc. / people.com, Ziff
Davis / askmen.com, Maxim, and Condé Nast / Glamour. `docs/SOURCE-HUNT.md`
records the surfaces already checked, so a proposed new source is probably
already in there with a reason.

**Do not commit an IMDb `.tsv.gz` dump.** They are about 2 GB and not ours to
redistribute. Derived artifacts are fine. `.gitignore` blocks them.

**Do not weaken the two standing constraints.** No image is fetched, attached or
shown to any model, and no age arithmetic exists anywhere in the scoring path.
`tests/test_no_age_formula.py` enforces both. A change that trips it is a design
change, not a test failure.

## Subject matter

This repository ranks named real people on a model's opinion of their
appearance. If you are proposing a change that adds people, adds a board, or
publishes a ranking more widely, say so plainly in the pull request and expect
that part to be discussed on its own terms rather than as an implementation
detail. Note in particular that the roster was chosen on prominence *before*
anything was scored, and that nobody is removed from it by name — the filters
that decide who is ranked are mechanical and print what they hide.

## Licence

No licence has been chosen yet, so default copyright applies and no permission
to reuse is granted. Open an issue if you need one before contributing.
