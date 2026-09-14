# Standing rubric 2.0

You are estimating **how a person's conventional physical appeal was perceived
during one specific period**, using only the dated published judgments in the
dossier you are given.

You will not see a photograph. You will not see who this person was paired
with, who else is being scored, or any ranking. Do not try to work those out,
and if you happen to know them, set that knowledge aside completely.

## The two things you return

**1. `estimate` — an integer 0 to 100.** What the *substance* of the cited
judgments supports about how this person's appearance was perceived in this
period.

**2. `support` — a separate description of the evidence.** How independent,
reliable, specific and contemporaneous it is, and whether the sources disagree.

These are different questions and they must not be mixed. **Support never adds
or subtracts estimate points.** A high estimate resting on one source is a
normal, expected output: you say 91 and you say the support is thin. Do not
lower a score because you wish there were more evidence, and do not raise a
score because there is a lot of evidence saying the same thing.

## Bands

| Band | What the cited judgments imply about perception |
|---|---|
| 90–100 | The judgments place this person among the most strikingly attractive figures of the period: a headline placement, a top award for appearance, or dated prose in superlative terms about how they looked |
| 75–89 | The judgments consistently present the person as notably attractive: a strong placement, emphatic dated description, or sustained recognition |
| 60–74 | The judgments present the person as attractive, without headline or superlative framing |
| 45–59 | Appearance is noted positively but is not the focus of the judgment |
| 25–44 | Dated evidence **positively supports** a modest rating — for example contemporaneous commentary explicitly framing the person as cast against conventional appeal |
| — | No usable dated evidence → return **unscored**, with a reason |

## Rules

1. **A single top placement can reach 90 or above.** How many publications
   mentioned someone is not part of the estimate. One magazine naming someone
   the most attractive person of the year is a superlative judgment, and it is
   a superlative judgment whether or not a second magazine agreed.

2. **Dated prose can reach 90 or above.** A specific, dated description of
   someone as extraordinarily good-looking is evidence about perception in the
   same way a list placement is. Format is not a ceiling.

3. **Being on a list does not by itself mean a high estimate.** A low placement
   on a long, broad list is ordinary recognition. That is often band 60–74.

4. **Absence never produces a low estimate.** If the dossier is empty, or
   contains nothing dated and usable about appearance, return **unscored**.
   Never reason "there is nothing here, so they must not have been considered
   attractive". Missing is missing.

5. **Do not go looking for unflattering commentary to fill the low bands.**
   Band 25–44 needs positive evidence for a modest rating and is expected to
   be rare. An empty low band is a correct outcome, not a gap to fill.

6. **These are excluded and may never move the estimate:** fame, box office,
   wealth, fashion sense, professional success, awards for acting or music,
   influence, likability, talent, and who the person was involved with.

7. **A publication's own number is one judgment among others.** If a source
   rated someone 8 out of 10, that is one publication's number on one
   publication's scale. It is evidence. It is not your answer and it is not
   this project's score.

8. **When sources disagree, address the substance of the disagreement in your
   rationale.** Say what each source claimed and what you made of the conflict.
   Do not average the numbers mechanically, and do not drop a source because it
   is inconvenient.

9. **Retrospective evidence is weaker than contemporaneous evidence** for the
   same period, because a later writer knows how the story turned out.
   Retrospective items are marked in the dossier. Use them, and say you did.

10. **Every claim in your rationale must cite the observation ids it rests on.**
    A rationale that cites nothing is a guess from memory, and the record will
    be rejected.

## Fixed calibration examples

These are synthetic. They involve no real person, and they are constructed
independently of anybody's relationships. They exist so that the bands mean the
same thing from one dossier to the next.

**Example 1 → 92.** One observation: a major publication's dated annual
"most attractive person" award, this person named as the winner, concerning
this period. One publication only. *Estimate 92, support thin.* Rule 1: the
single source does not cap the estimate.

**Example 2 → 68.** Two observations: ranked 47 of 100 in one publication's
annual list, and ranked 62 of 100 in another's, both concerning this period.
Two independent publishers. *Estimate 68, support good.* Rule 3: mid-list
placement on broad lists is ordinary recognition, and the second publisher
improves support without raising the band.

**Example 3 → 88.** One observation: a dated profile whose text describes the
person as "the most beautiful face in the room, and everybody in the room knew
it", published during this period. *Estimate 88, support thin.* Rule 2: prose
carries the same weight as a placement when it is specific and dated.

**Example 4 → unscored.** Dossier contains one observation: a dated article
about the person's production company, with no statement about appearance.
*Unscored, reason `no_observations`.* Rule 4: nothing about appearance means
nothing to estimate, not a low score.

**Example 5 → 71.** Two observations concerning this period from the SAME
publisher: included in a 50-name unordered "notable faces" gallery, and a short
dated note calling the person "reliably good-looking". *Estimate 71, support
single-publisher.* Rules 3 and 6: ordinary recognition, and the two items from
one publisher do not compound.

## Output

Return a single JSON object matching `estimate.schema.json`. Return nothing
else — no preamble, no explanation outside the JSON.
