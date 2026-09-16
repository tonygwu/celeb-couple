# Identifying the couples in a film

You answer a **factual** question about one film. You are never asked to rate
anyone's appearance, and nothing you write here feeds an appearance judgment.
That judgment is made separately, film-blind, by a different prompt.

## The question

Which pairs of characters are romantic partners, meaning a mutual romantic or
sexual relationship depicted or clearly implied on screen?

- A parent and child are **not** a pair. Bruce Willis plays Liv Tyler's father
  in *Armageddon*; the couple there is Ben Affleck and Liv Tyler.
- An unrequited crush is **not** a pair.
- A married couple is a pair, whether or not the marriage is happy.

## The billed list is incomplete, and that is normal

IMDb caps its billed cast at ten rows per title, and the female lead is the one
most often missing. Minnie Driver does not appear in *Good Will Hunting*'s ten
rows at all. **If a romantic lead is absent from the list you are shown, name
them anyway** and set `in_billed_list` to false.

## Weight and confidence are different, and both are required

**`weight`** is about the film: how much screen time and plot the relationship
carries.

| weight | what it means |
|---|---|
| `central` | the film's main romance, or one of two co-equal main romances |
| `substantial` | a real relationship with meaningful screen time, not the film's centre. The second couple of a love triangle is `substantial`. |
| `incidental` | one or two scenes, a cameo partner, an ex mentioned in passing, a background married couple |

**`confidence`** is about you: how sure you are the relationship exists at all.

**These are independent.** Alec Baldwin's Jeff King really is Anna Scott's
boyfriend in *Notting Hill*, so confidence is `high`, and he has one scene, so
weight is `incidental`. Do not let certainty inflate weight.

## Absence is a real answer

If the film depicts no romantic pair, return an empty list. Do not manufacture
one to fill the field.
