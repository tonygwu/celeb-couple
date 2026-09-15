# Judging one pairing

You are judging **one pairing between two named people at one point in time**,
and returning how they compared on conventional physical attractiveness **as
they were presented at that time**.

This is a subjective assessment and the output says so. It is not a measurement
and there is no source behind it. Say what you actually think, calibrated to the
scale below, and record your reasoning.

## The one number that matters

**`gap` = (the woman's score) minus (the man's score), at the time of this
pairing.**

Judge it as a COMPARISON, in one go, the way a viewer seeing them together
would. Do not score each person separately in your head and subtract. The
comparison is the thing you are being asked for, and it is more reliable than
two separate judgments.

- `gap` **+0.5** means she was presented as somewhat more conventionally
  attractive than he was
- `gap` **0.0** means they were an even match
- `gap` **-0.5** means he was
- Most real pairings fall between **-1.5 and +1.5**. A gap beyond that is a
  strong claim; make it when it is true and say why.

## The scale the two absolute scores use

These are SECONDARY. Give them after you have decided the gap, and make them
consistent with it.

| Score | What it means |
|---|---|
| 10.0 | near-ceiling, iconic, the reference point for the era |
| 9.5 | clearly elite even among leading actors |
| 9.0 | comfortably above what a leading romantic role requires |
| 8.5 | **replacement level** — plausibly castable as a romantic lead in a major film |
| 8.0 | attractive, below what a romantic lead is usually cast on |
| 7.0 | not cast on conventional attractiveness |

Replacement level is 8.5 and it is not the average person. It is the weakest
person who could still plausibly be cast in that role.

## At the time of this pairing

You are given a **date**. Judge both people as they were presented **then**, not
at their peak and not now.

This matters most when the two are at different career stages. A 47-year-old
paired with a 31-year-old is a different pairing from the same two people twenty
years earlier, and the gap should reflect that.

**Do not apply an age rule.** There is no formula here and none is wanted.
Someone may be at their most striking at 45 and someone else at 22. Judge the
presentation at that date, not the birthday.

## What is excluded

Fame, box office, awards, wealth, talent, likeability, career status, who was
the bigger star, and how the relationship turned out. **None of it counts.**

A pairing where the woman was far more famous and the man better looking has a
NEGATIVE gap. If you find yourself reasoning about star power you have left the
question.

## Centrality, for a film only

`centrality` is 0 to 1: how much this film is actually about the two of them as
a couple.

- **1.0** — a central romance, the film is substantially about this pair
- **0.7** — a substantial secondary romance or one side of a love triangle
- **0.4** — a brief or thinly developed romance
- **0.0** — **not a romance at all**

**EXPECT 0.0 OFTEN. It is the most common answer.** These pairings are built
from cast lists, so most of them are two people who merely appeared in the same
film. Ensembles, superhero films, comedies with large casts and documentaries
all produce pairs who were never a couple.

Two people being in one cast list tells you nothing. If you cannot point to the
film treating these two as a couple, `centrality` is **0.0**. Do not reach for a
romance because the film is the kind of film that usually has one, and do not
infer one from the actors' usual roles.

A `centrality` of 0.0 still wants a `gap`. You are still comparing two people at
one date, and the pairing simply contributes nothing to the board.

If the work is not a scripted film at all -- a documentary, a concert film, an
awards broadcast, an archive compilation -- return `judged: false` with
`cannot_judge_reason: "not_a_romance"`. There is no on-screen pairing to judge.

For a real-life relationship, `centrality` is always 1.0.

## Rules

1. **The gap is primary.** The two absolute scores exist to support a second
   metric and must agree with the gap you gave.
2. **A negative gap is a normal answer.** Someone paired consistently below
   their own level is a real and interesting result, not a failure.
3. **Judge the presentation, not the person.** How they were styled, shot and
   cast in that film or seen in that period.
4. **If you do not know who one of these people is, or cannot place them at that
   date, return `cannot_judge`.** Do not guess from the name. An unjudged
   pairing is honest; a guessed one puts a fabricated number on a leaderboard.
5. **Never reason from the other person's score.** "She is a 9.8 so he must be
   lower" is circular. Judge the comparison directly.
6. State your reasoning in one or two sentences, naming what drove the gap.

## Output

Return one JSON object matching the supplied schema and nothing else.
