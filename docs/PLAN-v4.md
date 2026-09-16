# Plan v4 — the leaderboard you actually asked for

**Status: draft for approval. Nothing in here has been run.**

v3 built a careful measurement instrument and it answered its own question with a
no: the permitted evidence cannot fill a pairing board. 1 comparable pairing out
of 228. v4 changes the one decision that caused that, keeps everything else, and
adds the thing the ChatGPT version is missing.

---

## 1. The single change

| | v3 | v4 |
|---|---|---|
| Where a score comes from | dated third-party published evidence, summarised | **the judge's own assessment** |
| Coverage | 42 observations over 100 people | every pairing gets a judgment |
| What blocks it | restricted publishers, thin sources | nothing |
| What it costs | — | the numbers are no longer traceable to a source |

Everything downstream of scoring carries over unchanged. The metric, the pairing
graph, the mirroring, the error bars, the reporting.

## 2. The constraint this reverses, stated plainly

Plan v3 carries, from the operator:

> "No face/body analysis, visual scoring, human photo-rating task, or automatic
> age-decline formula should re-enter the revised plan."

**v4 reverses the "visual scoring" half of that.** The judge is asked how
conventionally attractive real, named people were presented as being, and the
output is a ranked list of them. Two parts of the original constraint STAY
reversed only as far as necessary and no further:

- **No image is fetched, analysed, or shown to any model.** The judge works from
  what it already knows. There is no face analysis and no photo-rating task.
- **No age-decline formula.** v3 banned an automatic one and v4 still bans it.
  A pairing is judged at its own date. If an estimate falls as someone ages,
  that is the judge's per-pairing assessment, never a curve applied by code.
  A test asserts no age term exists anywhere in the scoring path.

The repository was private when this plan was written. Publishing it is a
separate decision that this plan does not ask for and does not prepare. If the
repository is public when you read this, that decision was taken elsewhere and
nothing in this plan should be read as having authorised it.

## 3. The metric — unchanged, and already built

This is ChatGPT's formula, and `modules/analytics/metrics.py` already implements
it with exact `Fraction` arithmetic and property tests:

```
PAW-WAR_i     = C_i * (F_i - M_i)        per pairing, signed, mirrors exactly
Partner_WAR_i = C_i * (F_i - B)          B = replacement level, frozen
PAW rate      = PAW-WAR / scored exposure
```

`C_i` is relationship centrality, 0-1. `scripts/classify_romance.py` already
produces it for on-screen pairings: a primary romance counts more than a brief
one, and a co-appearance that is not a romance counts zero.

Negative WAR is allowed and is the point. Brad Pitt scoring negative is the
statistic working, not failing.

## 4. The scoring change: ask for the GAP, not two scores

**The single most important design decision in this plan.**

v3 scored each person separately and subtracted. Two absolute judgments made in
different calls drift against each other, and labelling that drift is the entire
reason `comparability` exists. The metric never needed two absolutes. It needs
`F - M`.

So one call covers one pairing and returns, together:

```json
{"gap": 0.4,            // F - M, the primary quantity, one relative judgment
 "f_absolute": 9.8,     // secondary, for Partner_WAR only
 "m_absolute": 9.4,
 "centrality": 1.0,
 "rationale": "..."}
```

Why this is better, concretely: the judge compares two people **in the same
context, in one act of judgment**, exactly as a viewer of that film would. It
cannot drift between calls because there is no second call.

`f_absolute` and `m_absolute` are recorded but demoted. `Partner_WAR` depends on
them and carries a caveat saying so. `PAW-WAR` depends only on `gap`. Where the
two metrics disagree, `PAW-WAR` is the one to trust.

## 4a. AMENDMENT (2026-09-15): the judgment is film-blind and evidence-anchored

**This reverses §4's "ask for the GAP, not two scores", and the reason is
measured rather than argued.**

### What §4 got wrong

§4 was right that two absolute judgments made in different calls drift. It was
wrong about where the drift came from. The pairing prompt told the judge which
film it was scoring:

> A film: **Just Go with It**, released 2011.
> Judge them as they were presented IN THAT FILM.

So the same person in the same year was judged repeatedly, once per film, in a
different context each time. Measured on the M1 corpus:

- 57 of 363 (family, person, year) tuples were judged in more than one pairing
- mean spread 0.161, median 0.10, **max 0.50**
- **15 of 57 moved MORE than the 0.28 points by which the two judge families
  disagree with each other**

Angelina Jolie in 2000 came back 9.0 and 9.5 from the same judge. A judge
disagreeing with itself more than two different model families disagree is not
signal, and asking for the gap did not prevent it: the gap was stable while the
underlying scores were not.

### What replaces it

One judgment per **(person, year)**, film-blind, cached, reused everywhere that
person-year appears. `rubrics/person/`, `scripts/score_person_periods.py`.

The prompt never names a film, a co-star or a relationship, because none of them
should change how attractive someone was perceived to be in a given year.
Styling is a property of a production; this scale is a property of the person in
that year.

### The cost, stated

The gap becomes a SUBTRACTION of two independently judged scores, which is what
§4 set out to avoid. What makes the trade acceptable is that neither score is
anchored to a film any more, so they are no longer drifting between contexts —
which was the actual mechanism. The risk that remains, and is NOT yet measured:
a person judged with no partner in front of them may score differently than one
judged in a pairing. That is a designed probe, not an assumption, and it is
filed rather than waved away.

Caching does **not** save calls. 119 judged pairings need 215 distinct
person-years, and one pairing call already returned both scores plus the gap.
This is a correctness change that happens to be cacheable, not a cost
optimisation.

### Evidence-anchored

131 dated observations — awards and ranked placements, reported by Wikipedia —
sat unused because they are facts about a person in a year and the per-pairing
rubric had nowhere to put them. They are now attached to the judgment when they
exist, for 33 of 215 person-years.

This answers the weakness §9 names first: *"the numbers are unfalsifiable."*
They are still subjective, but 33 of them now rest on something a reader can
check, and every score records whether evidence was used and which ids it cites.

**Absence is stated, never implied.** When no observation exists the prompt says
so and tells the judge that absence is normal and is not evidence of a low
score. Silence would otherwise read as a signal.

The restricted-publisher rule is untouched. People Inc., Ziff Davis, Maxim and
Condé Nast are still never fetched by any route. These observations are
Wikipedia's CC BY-SA reports of what those publications said, which is how v3
collected them.

### The backlog

The cache makes the corpus grow incrementally. `--backlog-only` prints what is
uncached and spends nothing; `--limit N` grades part of it. The cache is written
after EVERY call, not at the end, so a run the machine sleeps through keeps
every tuple it paid for.

## 5. Error bars — what this adds over the ChatGPT version

ChatGPT states +/- 0.2-0.3 uncertainty per score. Its leaderboard is then decided
by these numbers:

```
1 Ben Affleck   +0.34     4 Ryan Gosling      +0.30
2 Tom Cruise    +0.34     5 Leonardo DiCaprio +0.14
3 Richard Gere  +0.39
```

Each is a difference of two scores, so its uncertainty exceeds +/- 0.3. **The top
four are separated by 0.09 against error bars around +/- 0.4.** By its own stated
numbers that ordering is indistinguishable from noise.

This project already has the apparatus to fix that, built and tested:

1. **Repeat measurement.** A sample of pairings is judged four times.
   `scripts/measure_rater_noise.py` returns a least significant difference: how
   far apart two numbers must be before the difference means anything.
2. **Two judge families.** fable and astra. On 2026-09-15 they differed by 1.5 to
   2.25 points on identical dossiers, which is far larger than the gaps deciding
   the list above.
3. **Rank stability.** Resample within the error bars and report how often each
   rank holds. A leaderboard row reads `#3 (holds 62% of resamples)` or it does
   not ship.

**Every board states which rank differences are real.** That is the deliverable
that does not currently exist anywhere.

## 6. The four leaderboards

| # | Board | Unit of a "season" | Source of pairings |
|---|---|---|---|
| 1 | Male actors, on-screen | one film | co-star + romance classifier |
| 2 | Male actors, real life | one relationship episode | Wikidata, human-reviewed |
| 3 | Female actors, on-screen | one film | same as 1, mirrored |
| 4 | Female actors, real life | one relationship episode | same as 2, mirrored |

Boards 3 and 4 are **not** separate research. `Pairing.mirror()` already exists
and the mirrored-gap invariant is property-tested: a gap of +0.4 on the men's
board is -0.4 on the women's, exactly, in every draw.

Each board ships in two forms, because they answer different questions:
**cumulative** rewards a long career, **rate** rewards a high average.

## 7. What carries over, what retires

**Carries over unchanged**

- the metric module and its property tests
- 253 real-life relationship episodes over the 100-name roster, 232 inside the
  adult window, 246 distinct couples
- the romance classifier, which is `C_i`
- date precision handling: a year is `"1984"`, never `1984-01-01`
- the grading contract, the stale-contract guard, the one-escalation rule
- repeat measurement, two-judge reduction, band-based adjudication
- the whole reporting and doc-audit chain

**Retires, with its reasoning kept in `docs/`**

- `comparability` — it labelled drift between two independent absolute scores,
  and a single relative judgment has no drift to label
- the observation corpus, the source-access matrix, `absence_audit`, the
  publisher restrictions. **The restricted-publisher rule stays in force as a
  fetching rule.** Nothing fetches from People Inc., Ziff Davis, Maxim or
  Conde Nast under this plan either, because nothing fetches at all.

**The v3 evidence corpus is kept, not deleted.** It becomes the validation set:
where a published dated award exists, does the judge's assessment agree with it?
That is the only external check available and it costs nothing to run.

## 8. Budget and staging

Counts are real where measured and marked where not.

| Stage | Pairings | Calls (1 family) | Notes |
|---|---|---|---|
| M1 pilot slice | ~40 | ~40 | 10 actors, both domains, validates the whole path |
| M2 real-life, full | 232 | 232 | measured: adult-window scorable episodes |
| M3 on-screen, full | **unmeasured** | ? | needs a free Wikidata fetch to size |
| M4 repeats for error bars | 10% x 4 | ~110 | the thing that makes the boards honest |
| M5 second family | sample, not all | ~100 | calibration, not a full second pass |

**M3 is the unknown and it is the one that could be large.** The pilot found 20
co-starring films for 14 people; co-star pairs grow faster than the roster does.
Size it with a free fetch BEFORE approving any spend on it.

**Do not approve the whole thing at once.** Approve M1. It costs about 40 calls,
exercises every piece, and produces a real 10-actor board with error bars. If the
error bars swallow the ranking at that scale, more spend will not help and you
will have learned that for 40 calls instead of 1200.

## 9. What could go wrong, honestly

- **The numbers are unfalsifiable.** No source backs them. The validation set in
  §7 is a weak check and the only one available.
- **The judge's priors are the measurement.** Whatever the training data encodes
  about who is attractive is what this reports. Two families disagreeing by 2
  points is evidence that this is not a stable quantity.
- **The error bars may swallow the leaderboard.** This is the likeliest outcome
  and M1 is designed to find it early and cheaply. If it happens, the honest
  product is a board with wide intervals and few distinguishable ranks, which is
  still more than anyone else has.
- **It is a ranked list of real people by attractiveness.** Private is private.
  Publishing is a separate decision with separate consequences, and this plan
  neither asks for it nor prepares it.

## 10. Stop condition

**Stop after M1** and show the 10-actor board with its error bars. M2 onward
needs a second approval, and M3 needs its free sizing fetch first.

## 11. AMENDMENT (2026-09-15): IMDb admitted, and why the roster was the bottleneck

### The problem this solves

§6's boards are thin. Five people on the men's on-screen board. The method is
sound after §4a, and the corpus is not there.

The cause is not the judging and not the budget. It is that **Wikidata records
`cast member` (P161) but almost never records who played the love interest.**
So roster expansion had to snowball over co-starring, which ranks people by how
often they appear beside someone already on the list. That ranking does not
track romantic billing. Drew Barrymore came in at rank 169. Minnie Driver came
in at rank 455 and had to be named by hand. A bigger cap does not fix a ranking
that is measuring the wrong thing.

### What changed

Plan v3 §3 listed IMDb as `Out` over its terms clause about repurposing the
data into a movie database. **The operator reversed that on 2026-09-15**, for
full use including the published page. `docs/SOURCE-HUNT.md` carries the
reasoning and the cost that was named before the choice.

### Why it is the right lever

`title.principals.tsv.gz` gives billing order for every title, so "the two
top-billed leads, one `actor` and one `actress`" becomes a mechanical rule over
the whole corpus rather than a snowball. Three things arrive with it:

- **`ordering`** — billing position, which is what "lead" means.
- **`category`** — literally `actor` or `actress`, so sex comes from the file
  and not from an inference over first names.
- **`characters`** — character names, a second signal for a romance beyond
  billing and genre.

### What this does NOT change

- The judgment stays **film-blind**, per §4a. The judge is never told the film.
  IMDb decides *who* gets scored and never *what the score is*.
- The restricted publishers stay restricted, by every route.
- Every score stays keyed on `(person, year, family)` and stays cached, so
  widening the roster costs only the person-years that are new.

### The open question this re-opens

§8's budget was sized against a 100-name roster. A corpus built on billing
order will be larger. The budget has to be re-derived from the new graph before
anything is judged, and the operator sets the number.
