# Roster backlog — scope the product must not quietly lose

The pilot cohort is 14 Hollywood film actors. The 100-name draft roster in the
plan is also actor-centric. That is a convenience of the pilot, **not** the
intended product, and this file exists so the final board does not silently
become "the actors who happened to be easiest to score".

Filed 2026-09-14. Nothing here is verified or scheduled.

## Scope that is in the plan and not yet in the data

### Real-life mode is open to music and entertainment figures with no film career
Their on-screen state is "no eligible records", never a zero. The pilot has none
of them, so the pipeline has never been exercised against a subject whose entire
record is real-life. **Difficulty: medium** — the records path already works on
Wikidata P26/P451 and does not care whether the person acts.

### Classic-film contenders
The cohort's earliest evidence is 1985, because Sexiest Man Alive started then
and People's Most Beautiful started in 1990. Anybody whose career ran before the
mid-1980s has no permitted award-shaped evidence at all. Candidates worth a
look, with their pairings, if a pre-1985 permitted source is ever found:
Cary Grant, Elizabeth Taylor, Paul Newman, Joanne Woodward, Richard Burton,
Sophia Loren, Marcello Mastroianni, Grace Kelly, Steve McQueen, Ali MacGraw,
Warren Beatty, Julie Christie, Robert Redford, Faye Dunaway.
**Difficulty: hard** — blocked on evidence, not on code. See the source hunt below.

### Non-US markets
FHM's list is UK-facing and its pool is explicitly not the same pool as a US
Hollywood list, which the record already says in `candidate_set_described`. A
board mixing pools without saying so would be comparing different populations.
**Difficulty: medium** — needs a pool-comparability rule, not more scraping.

## Source hunt, ranked by what it would actually buy

Measured 2026-09-14: award-shaped evidence cannot discriminate. Twelve
editorial-award person-periods scored exactly 92.0; the single ranked
observation scored 86.5. **Only ordered, depth-carrying lists change the
product.** More award sources add coverage and change nothing about the board.

1. **Ordered lists with US/Hollywood depth.** FHM gave 206 ranked positions and
   exactly one cohort member, because its pool is British TV and modelling.
   This is the single highest-value open item. **Difficulty: hard.**
2. **Pre-1985 permitted evidence of any shape.** Unlocks the classic-film
   contenders above. **Difficulty: hard.**
3. Dated snapshots that pin a continuously-updated crowd list to a date, which
   is the only way Ranker-style sources become historical evidence.
   **Difficulty: medium.**
4. Publishers currently isolated pending a terms read: tccandler (permissive
   robots, terms unread), and the full site terms for Maxim and Condé Nast.
   **Difficulty: easy, but may end in "still out".**

Restricted and not to be revisited without new information: people.com and
askmen.com forbid LLM extraction and dataset creation in their terms, by every
route including archives.

## Method work the pilot deferred

- **Repeat-scoring across more than two dossiers and more than one family.**
  Tonight's rater SD of 0.0 rests on one judge, because codex reached 0% quota
  mid-run. **Difficulty: easy, blocked on quota until codex resets.**
- **A ranked-evidence corpus large enough to measure spread properly.** One
  ranked observation established that ranked evidence discriminates. It cannot
  establish by how much. **Difficulty: blocked on item 1 above.**
- **Human grounding read.** `docs/GROUNDING-AUDIT.md` is generated and waiting;
  25 of 26 rationales are flagged for a person. **Difficulty: easy, needs a human.**
- **Pool comparability between lists drawn from different populations.**
  **Difficulty: medium.**
