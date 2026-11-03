---
name: score
description: Score every card in one or more of your Commander decks with the fit-score metric (independent scorers, median), write output/decks/<slug>/nonlands.md and lands.md, optionally recompute output/decks/rankings.md. Use when asked to score, rescore or re-evaluate a deck's cards, or after a plan or metric change.
---

# score

The metric lives in the `commander-deckhand:scorer` agent,
`${CLAUDE_PLUGIN_ROOT}/agents/scorer.md`; the owner tunes it there, this
skill only applies it. Scores are never hand-edited: when one looks wrong,
fix the metric or the deck's `plan.md` and rescore.

Inputs per deck: `output/decks/<slug>/list.txt`, `plan.md` (authoritative),
the Card columns of the `## Adds` tables in `nonlands.md` and `lands.md`
(adds are scored too), `output/data/oracle.json`.

`settings.json`, beside `output/`, sets `scorers`, the scorers per deck
(default 3), and `model`, the model every agent here is dispatched on
(default `claude-opus-5-5`, the agents' own); an absent file or key takes the
default. Every agent here runs `run_in_background` in the folder that holds
`output/`, with `model` passed only when it differs from the default; its
prompt carries only the per-run inputs named below, since the agent holds
its standing instructions.

1. If Moxfield's `lastUpdatedAtUtc` may be newer than the list, run
   `commander-deckhand:sync` first.
2. Make a fresh scratchpad folder `<run>/`. Group decks by shared colours
   (three or so per group). Dispatch `scorers` `commander-deckhand:scorer`
   agents per group, lettered A, B, C and on, each prompt giving `<run>`,
   the letter, the scorer's own `<run>/work-<group>-<letter>/` subfolder
   (two scorers sharing one overwrite each other's helpers) and the group's
   slugs, each with its bracket from `output/decks/rankings.md`.
3. When all of a group are back:
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/merge.py <run> <slug>`.
   It writes `<run>/merged/<slug>/nonlands.md` and `lands.md` with the
   Adds and Cuts tables carried over from the current pair and this run's
   scores, the shape line recording the count of scorers, and prints the
   whole deck's shape line. One scorer's scores stand as they are; with
   two or more it takes the median, writes `<run>/<slug>-flagged.md` with
   the split cards, those whose scores differ by 3 or more, each with every
   scorer's score and note, and prints their count.
4. Copy each deck's merged pair into `output/decks/<slug>/`. Check the shape
   line merge.py printed for each deck against rule 8 of the metric.
5. If more than one deck was rescored, or the owner asks, recompute the
   rankings with one `commander-deckhand:ranker`, its prompt giving `<run>`;
   copy `<run>/rankings.md` over `output/decks/rankings.md`.

Report: per deck the shape line, the 10s and the split cards in one line
("split: X, Y"), a sign the plan is unclear on them, since the owner's fix
for a disputed score is the plan or the metric; anything that moved by 3 or
more since the last scoring.
