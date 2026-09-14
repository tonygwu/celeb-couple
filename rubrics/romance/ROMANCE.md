# On-screen romance classification

You are deciding one thing about one film: **do the characters played by these
two named actors have an established, reciprocal romantic relationship in the
film itself?**

You will be given the film's plot summary and the two actors' names. Judge from
the plot text you are given. Do not use anything you remember about the film.

## What qualifies

`reciprocal_romance` — the plot shows the two characters as a couple, or
falling for each other mutually, or married, or in an established relationship.
Both sides must be in it.

## What does NOT qualify

- `co_appearance_only` — both are in the film with no romantic link between
  their characters. **This is the default.** Two actors in one cast list tells
  you nothing.
- `unrequited` — one wants the other and it is not returned. One-sided.
- `brief_or_incidental` — a single kiss, a flirtation, a one-scene encounter
  that the plot does not treat as a relationship.
- `family_or_platonic` — related, or friends, or colleagues.
- `coerced_or_assault` — the plot describes coercion or assault. **This is
  never scored as a romantic pairing**, and classifying it as one would treat
  an assault as an accomplishment.
- `cannot_tell` — the plot text does not say, or does not mention one of the
  characters at all.

## Rules

1. **Billing order, screen time and marketing prove nothing.** Only what the
   plot says about the two characters counts.
2. If the plot text does not mention one of the two actors' characters, return
   `cannot_tell`. Do not reason from the actor's usual roles.
3. Your `evidence` must be a short verbatim quote from the plot text you were
   given. No quote means `cannot_tell`.
4. A romance between one of these two and a THIRD character is not a pairing
   between these two.
5. Prefer `cannot_tell` over a guess. An unclassified film is honest; a wrong
   classification puts a couple on a leaderboard who were never a couple.

## Output

A single JSON object matching `romance.schema.json`. Nothing else.
