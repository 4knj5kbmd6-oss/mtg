---
name: score
description: Score every card in one or more of your Commander decks with the fit-score metric (independent scorers, median), write output/decks/<slug>/nonlands.md and lands.md, optionally recompute rankings.md. Use when asked to score, rescore or re-evaluate a deck's cards, or after a plan or metric change.
argument-hint: "[slug ...] [key=value ...] | <slug> <card name> [<card name> ...]"
---

# score

The metric lives in the `mtg-deckhand:scorer` agent,
`${CLAUDE_PLUGIN_ROOT}/agents/scorer.md`; the owner tunes it there, this
skill only applies it. Scores are never hand-edited: when one looks wrong,
fix the metric or the deck's `plan.md` and rescore.

Read `settings.json` through `settings.py`
(`python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/settings.py`), passing it
every `key=value` word of the arguments, which overrides that setting for
this run (a dotted key, `quota.adds=15`, reaches a nested one); dispatch each
agent with `model` only when it differs from the agent's own. Every agent
here runs `run_in_background` in the folder that holds `output/`; its
prompt carries only the per-run inputs named below.

1. If Moxfield's `updated` may be newer than the list, run
   `mtg-deckhand:sync` first.
2. Make a fresh scratchpad folder `<run>/`. Group decks by shared colours
   (two or three per group). Dispatch `scorers` `mtg-deckhand:scorer`
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
   rankings with one `mtg-deckhand:ranker`, its prompt giving `<run>`;
   copy `<run>/rankings.md` over `rankings.md`.

Card names after a slug, `/score <slug> <card name> [<card name> ...]`,
score only those cards for that deck, usually a card just added through
`changes.md`. A card not in the deck's `list.txt` is a candidate, scored as
if added; one missing from `oracle.json` is fetched into it first with
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch-oracle.py "<card name>" ...`,
which reports any name Scryfall does not know. Run steps 2 to 4 for that
deck alone, each scorer's prompt also naming the cards. merge.py sees tables
holding fewer of the list's cards than it has and patches the deck's
`nonlands.md` and `lands.md` instead of rewriting them: a listed card's row
replaced or inserted in the Cards table in score order and its Adds row
dropped, a candidate's row in the Adds table of the file its type belongs
to, in score order, keeping the New and ~Price of an Adds row it had, else
`-`; the Shape line recomputed. A later `/upgrades` rebuilds Adds from
research, so a candidate stays only while the research lists it too. The
ranker does not run.

Report: per deck the shape line, the 10s and the split cards in one line
("split: X, Y"), a sign the plan is unclear on them; anything that moved by
3 or more since the last scoring.
