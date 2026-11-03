---
name: score
description: Score every card in one or more of your Commander decks with the fit-score metric (independent scorers, median), write output/decks/<slug>/nonlands.md and lands.md, optionally recompute rankings.md. Use when asked to score, rescore or re-evaluate a deck's cards, or after a plan or metric change.
---

# score

The metric lives in the `commander-deckhand:scorer` agent,
`${CLAUDE_PLUGIN_ROOT}/agents/scorer.md`; the owner tunes it there, this
skill only applies it. Scores are never hand-edited: when one looks wrong,
fix the metric or the deck's `plan.md` and rescore.

Read `settings.json` through `settings.py`
(`python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/settings.py`); dispatch each
agent with `model` only when it differs from the agent's own. Every agent
here runs `run_in_background` in the folder that holds `output/`; its
prompt carries only the per-run inputs named below.

1. If Moxfield's `updated` may be newer than the list, run
   `commander-deckhand:sync` first.
2. Make a fresh scratchpad folder `<run>/`. Group decks by shared colours
   (two or three per group). Dispatch `scorers` `commander-deckhand:scorer`
   agents per group, lettered A, B, C and on, each prompt giving `<run>`,
   the letter, the scorer's own `<run>/work-<group>-<letter>/` subfolder
   and the group's slugs, each with its bracket from `rankings.md`.
3. When all of a group are back, per deck
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/merge.py <run> <slug>`. It
   prints the deck's shape line and, with two or more scorers, the count of
   split cards (scores 3 or more apart), listed in `<run>/<slug>-flagged.md`.
4. Copy each deck's merged pair, `<run>/merged/<slug>/`, into
   `output/decks/<slug>/`. Check the shape line merge.py printed for each
   deck against rule 8 of the metric.
5. If more than one deck was rescored, or the owner asks, recompute the
   rankings with one `commander-deckhand:ranker`, its prompt giving `<run>`;
   copy `<run>/rankings.md` over `rankings.md`.

Report: per deck the shape line, the 10s and the split cards in one line
("split: X, Y"), a sign the plan is unclear on them; anything that moved by
3 or more since the last scoring.
