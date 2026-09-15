# Extracting list memberships from biographical prose

You are reading one person's Wikipedia article. Find every **dated mention of
that person appearing on a published attractiveness list, poll or award.**

## What to extract

Anything of this shape:
- "named People's Sexiest Man Alive in 2018"
- "one of People's 50 Most Beautiful People" (with a year, stated or clearly implied by the sentence)
- "ranked 5th in FHM's 100 Sexiest Women 2007"
- "voted the sexiest man in a readers' poll in 2004"
- "named Essence's Sexiest Man of the Year in 2013"

## What NOT to extract

- **Critics describing a performance.** "the blandly handsome Affleck couldn't
  convince..." is a film review, not a list membership. This is the commonest
  false positive and it is not evidence of anything.
- Awards for acting, music, or any achievement other than appearance.
- Undated mentions. A membership with no year is useless here — skip it.
- Descriptions of the person as a sex symbol in general terms with no
  publication and no list named.
- Anything you know but the article text does not say.

## Fields

For each mention:
- `publisher` — the magazine, site or organisation. Exactly as named in the text.
- `list_name` — the list or award as named.
- `year` — four digits. Skip the mention if the text does not give one.
- `rank` — an integer ONLY when the text states a position. Otherwise null.
- `list_length` — an integer ONLY when the text states one. Otherwise null.
- `shape` — `ordered_rank` when a position is stated, `editorial_award` when
  the person is the single named winner, `unordered_inclusion` when they are
  named as one of a set.
- `evidence` — a VERBATIM quote from the article text containing the mention.

## Rules

1. Every mention needs a verbatim `evidence` quote from the text you were
   given. No quote, no mention.
2. Never infer a rank. "one of the 50 Most Beautiful People" is
   `unordered_inclusion` with `list_length` 50 and `rank` null.
3. Never infer a year. If the sentence does not carry one, skip it.
4. Return an empty list rather than a weak guess. Zero mentions is a normal,
   correct answer.

## Output

A single JSON object matching `mentions.schema.json`. Nothing else.
