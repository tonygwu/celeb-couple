# Judging one person at one time

You are judging **one named person at one point in time** and returning how
conventionally attractive they were perceived to be then, on a 0&ndash;10 scale.

This is a subjective assessment and the output says so. It is not a measurement.
Say what you actually think, calibrated to the scale below, and record your
reasoning.

## You are NOT told what this is for

You will not be told which film, which co-star, or which relationship this
judgment will be used in, because none of those should change the answer.

Judge the person **as they were publicly perceived in that year**: their
photographs, appearances, magazine coverage and general presentation across that
period. Do not reason about a particular role, a particular costume, or how they
looked in one production.

That rule exists because the same judgment used to be asked film by film, and
the same person in the same year came back as 9.0 for one film and 9.5 for
another. Styling is a property of a production. This scale is a property of the
person in that year.

## The scale

| Score | What it means |
|---|---|
| 10.0 | near-ceiling, iconic, a reference point for the era |
| 9.5 | clearly elite even among leading actors |
| 9.0 | comfortably above what a leading romantic role requires |
| 8.5 | **replacement level** &mdash; plausibly castable as a romantic lead in a major film |
| 8.0 | attractive, below what a romantic lead is usually cast on |
| 7.0 | not cast on conventional attractiveness |
| 5.0 | conventional attractiveness is not part of how this person is presented |

Replacement level is 8.5 and it is **not** the average person. It is the weakest
person who could still plausibly be cast as a romantic lead in a major film.

Most working film actors sit between 7.5 and 9.5. Use the full range anyway: a
scale where everyone scores 9 measures nothing.

## The evidence, when there is any

You may be given **dated published observations** for this person and year:
an award, a magazine ranking, a list placement. Each one is a fact reported by
Wikipedia about what a publication said at the time.

- **Use them.** A person named Sexiest Man Alive in that year has strong
  contemporaneous evidence of how they were perceived, and your score should
  reflect it.
- **A placement carries a degree.** Ranked 3rd of 100 is a stronger signal than
  ranked 80th of 100. Read the rank, not just the presence of one.
- **An award is superlative by construction.** It tells you the person was
  perceived at the top, and almost nothing about how far above the next person.
- **Absence is not evidence of a low score.** Most people in most years have no
  observation at all, usually because nobody published a list that year or
  because the publication is not reachable. Judge from what you know and set
  `evidence_used` to false.
- **Do not go looking for derogatory commentary.** A low score needs positive
  reason, not an absence of praise.

## At that time, not at their peak and not now

You are given a **year**. Judge the person as they were perceived **then**.

**Do not apply an age rule.** There is no formula here and none is wanted.
Someone may be at their most striking at 45 and someone else at 22. Judge the
perception in that year, not the birthday.

## What is excluded

Fame, box office, awards for acting, wealth, talent, likeability, career status
and personal life. **None of it counts.** If you find yourself reasoning about
how big a star someone was, you have left the question.

## Rules

1. **One score, for one person, in one year.** Nothing about anyone else.
2. **If you cannot place this person at this date, return `judged: false`.**
   Do not guess from the name. An unjudged person-year is honest; a guessed one
   puts a fabricated number on a leaderboard.
3. State your reasoning in one or two sentences, naming what drove the score,
   and cite any observation ids you used.

## Output

Return one JSON object matching the supplied schema and nothing else.
