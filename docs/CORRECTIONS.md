# Corrections to published numbers

A measurement project should keep a record of when its own numbers changed and
why, separate from the git log. This is that record.

**Nothing here overturned a conclusion.** Every finding in
[`docs/THE-TRAP.md`](THE-TRAP.md) held through every correction below, and two
of them held for a *better* reason afterwards. That is the useful part: the
conclusions were not resting on the figures that turned out to be wrong.

Read this if you read an earlier version of `docs/M0-REPORT.md`.

## 2026-09-15 — the bundled contract bump and the first two-family score

Three filed rubric corrections landed together, with the operator approving the
re-score they cost. `standing-rubric-2.0` became `2.1`, `mentions-1.0` became
`1.1`, and the hash scheme became `v2-length-prefixed`, which moved every
contract id including romance's, whose bytes never changed.

**Nothing below overturned a conclusion.** The comparable gap is still under the
noise floor, and the shape confound is now supported by better evidence than it
had before.

### The rank-shaped noise floor: 2.56 → 1.03, and the floor is not stable

Measured again with both judge families on the same four ranked dossiers. The
pooled figure is 0.69 and the rank-shaped one is 1.03, against 2.56 before.

**Do not read this as a more precise floor.** The same judge, on the same four
dossiers, gave these within-judge standard deviations on two runs:

| fable, ranked | Jolie 06 | Pfeiffer 95 | Aniston 96 | Aniston 97 | mean |
|---|---|---|---|---|---|
| previous run | 0.816 | 1.155 | 1.155 | 0.577 | 0.926 |
| this run | 0.500 | 0.000 | 0.000 | 0.577 | 0.269 |

A 3.4× difference in the noise measurement itself. Four dossiers at four repeats
does not pin this quantity, and quoting either number as *the* floor overstates
what was measured. Both are recorded; the conclusion holds against either.

### The one comparable gap: 0.0 → 0.5

Ben Affleck and Jennifer Garner, Daredevil 2003: 92.0 against 92.5, where both
were 92.0 before. The 92.5 is a mean of two judges, not a moved estimate.
Still far below the floor on either measurement. No leaderboard here either.

### Every across-judge gap: `None` → measured

`across_judges_gap` was null for all 39 person-periods, because codex ran out of
quota mid-run and one family scored everything. It is now non-null for all 40:
median 1.0, mean 1.62, max 8.0, with 18 exact agreements.

**`ADJUDICATION_GAP = 10.0` fires on nothing**, which is what `docs/BACKLOG.md`
predicted. The observed maximum is 8.0. Setting it is a methodology decision and
is left open.

### Corpus: 41 → 42 observations

Prose mentions were re-extracted under `mentions-1.1`: the cohort file went 12 →
10 and the partner file 6 → 7. Observations went 41 → 42, and verification is
still a full pass at 42 of 42.

### What the contract bump itself moved: nothing beyond rater noise

Disentangled from the second judge, because the headline estimates moved by up
to 10 points and almost all of that is the reducer now averaging two families
rather than one. No dossier changed its observation count. fable ALONE moved on
17 of 39 person-periods, mean absolute move 2.35 — below the 2.56 floor
published at the time, though above the 1.03 measured after. Two estimates moved
6 points.

The honest reading is that the rubric and schema edit produced no movement
clearly distinguishable from rater noise, stated against a floor that is itself
uncertain by a factor of three.

### A claim that was published to the operator and then withdrawn

Award-shaped evidence was reported as pinning two model families to the
identical number 72% of the time. That rate was nearly collinear with astra's
`effort_took_effect` flag, and `CodexJudge`'s own measurement note says that
flag cannot distinguish a mis-served request from a turn that needed little
reasoning. The observational cut could not support the claim.

**The repeat experiment can, and does.** Both award-shaped dossiers returned
exactly 92.0 on all 24 runs — two dossiers, four repeats, two families, two
separate runs, zero variance in every cell — while ranked dossiers produced
between-family gaps of 0.5 to 2.25. That is a controlled design rather than an
observational cut, and it does not depend on the effort flag at all.

## 2026-09-14 — the overnight hardening run

### The rank-shaped noise floor: 1.2 → 2.22 → 2.56 points

Corrected twice, for two different reasons.

**Pooling.** The figure averaged the within-judge spread across evidence
shapes. One dossier measured was rank-shaped and varied; the other was
award-shaped and returned the same value four times. Averaging a measured
variance with a zero halved the result, and the result was then applied to gaps
between rank-shaped estimates — the shape holding all of the variance. Quoted
per shape, the ranked figure was 2.22.

**Estimator.** That still used the POPULATION standard deviation on four repeat
scorings. Four runs are a sample of the rating process, not the whole of it, and
the population formula underestimates by about 13% at n = 4. The sample
standard deviation gives **2.56**.

The award shape gets no figure at all: two dossiers returned the same value on
all eight repeats, which cannot distinguish low variance from none.

Why it did not change anything: the one comparable pairing has a gap of 0.0,
which is below any of the three floors, and the format-equivalence stress case
spreads 4 points, which is above all three.

### Evidence shape explains: 39% → 31% of the variance

The published figure was eta-squared. Eta-squared is biased upward, and the
bias grows with the number of groups: this corpus has 39 estimates over five
shape groups, two of which hold a single estimate — and a group of one has its
mean equal to its value by construction. Omega-squared, the unbiased
estimator, gives **31%**. Both are now reported, with omega leading.

A third of the variance in an attractiveness estimate being explained by the
FORMAT of the evidence is decisive at either figure.

### Cohort coverage: "14 of 14 people" → 10 of 14

The report said the sources covered 14 of 14 cohort people and, in the same
paragraph, named five people with no evidence at all. The numerator counted
everyone carrying an observation — partners included — against a cohort-only
denominator, and the two happened to collide on the cohort size.

Partner coverage is now reported separately, because partner evidence is what
makes a pairing jointly covered. **10 of 14** cohort members have evidence and
four have none.

### Source-requirement ceiling, again: 25 of 239 → 14 of 228 episodes

The largest correction in this file, and it moved the project's most optimistic
number: how much joint coverage a perfect, permitted source could ever buy.

The roster's episode list counted the same relationship twice whenever both
people were on the roster. Wikidata records a marriage on BOTH items, the
fetcher read both, and `merge_progressions` saw two spans over the same dates
rather than two abutting ones. 12 roster pairs were duplicated that way.

Those duplicates were not a random sample of the corpus. A mirrored duplicate
exists ONLY when both partners are on the roster, and both-partners-on-the-
roster is the precondition for a pairing to be jointly covered at all. So the
duplicates fell entirely inside the population the simulation counts, and each
one was counted twice.

The arithmetic shows it: removing them took scorable episodes 239 → 228, a loss
of 11, and took the ceiling 25 → 14, a loss of 11. One for one. Had the
duplicates been spread evenly across the corpus, the ceiling would have fallen
by about one.

Verified by running `source_requirement.py` against both episode files with the
same seed (20260914) and the same 120 trials per rung, so the corpus is the
only thing that differs.

**The conclusion is unchanged and is stronger.** `docs/SOURCE-HUNT.md` says the
pairing board's source requirement cannot be met on a permitted route. The
ceiling being 6 percent of episodes rather than 10 does not rescue anything;
it makes the gap wider.

### Source-requirement ceiling: 22 → 25 of 239 episodes

The simulation drew each hypothetical annual list WITH replacement, so a rung
labelled "100 names per year" listed a median of 48 distinct people and no
deeper rung listed more. The curve's saturation was partly the sampler running
out of distinct draws.

Sampling without replacement — a published ranked list of 100 names has 100
distinct names — the ceiling is **25 of 239**, and it still saturates at 100
names a year, now because the roster is exhausted at that depth. The
requirement is unchanged and the saturation is real.

### Stress case S2 was reported as a pass, and then over-read

The format-equivalence case renders one substantive judgment as an award, as a
ranked placement, and as prose. It spreads 4 points, above the measured floor,
and was recorded as "formats scored comparably" against a threshold of 10 typed
before anything had been measured. That much was a straightforward correction.

It was then described in this report — by me, earlier the same night — as the
evidence-shape confound "measured under controlled conditions" and
"independent corroboration" of the observational figure above. **That was
wrong, and the evidence was in the rubric all along.**

S2's prose arm uses the VERBATIM text of the rubric's calibration Example 3,
which the rubric anchors at 88. Its award arm has the shape of Example 1,
anchored at 92. The observed arms were 92, 92 and 88 — the anchored values.

So S2 shows the judge following its calibration anchors, which is what anchors
are for and is worth knowing. It does not show that identical substance is
perceived differently in different formats, because the rubric told the judge
those two formats sit four points apart. Redesigning the case is filed in
[`docs/BACKLOG.md`](BACKLOG.md).

The observational shape figure is measured on real dossiers and is unaffected.

### Stress case S6 was reported as a failure

The identity-leakage case scored 82, 82.5 and 82 across named, anonymised and
identity-swapped arms. Its stored verdict said "identity moved the score". A
spread of 0.5 is below every floor this project has measured; identity did NOT
move the score.

### "Every comparable pairing will be 0.0" → most of them

Five sentences across the report and the capstone claimed that an award-shaped
estimate can only produce one value: *can only land in one band*, *produces the
same number every time*, *every one of those dossiers still lands in a single
band*, *cannot discriminate between winners*, and *every one of them will be
0.0*.

Each was exactly true when every award-shaped estimate was 92. Three of the
eighteen now are not — 78, 91 and 94 — and none of the five sentences was
revisited when the corpus grew.

Measured rather than assumed: of the 153 possible award-versus-award pairs in
this corpus, 105 are exactly equal, which is 68.6%. So a comparable pairing is
0.0 about seven times in ten, not always.

The conclusion is unchanged. Seven in ten comparable pairings landing on zero
still makes a board larger and very little more informative, which is the whole
argument. It never needed the absolute.

## What this record does not cover

Defects in code that never produced a published number, corrections to prose
that stated no figure, and the guards added to stop each class recurring. Those
are in the git log and in [`docs/BACKLOG.md`](BACKLOG.md).
