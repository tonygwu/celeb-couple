# Corrections to published numbers

A measurement project should keep a record of when its own numbers changed and
why, separate from the git log. This is that record.

**Nothing here overturned a conclusion.** Every finding in
[`docs/THE-TRAP.md`](THE-TRAP.md) held through every correction below, and two
of them held for a *better* reason afterwards. That is the useful part: the
conclusions were not resting on the figures that turned out to be wrong.

Read this if you read an earlier version of `docs/M0-REPORT.md`.

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
