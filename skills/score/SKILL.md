---
name: score
description: Score every card in one or more of your Commander decks with the fit-score metric (independent scorers, median), write output/decks/<slug>/nonlands.md and lands.md, redraw its changes.png, recompute rankings.md after a rescore of several decks or when a deck has no bracket yet. Use when asked to score, rescore or re-evaluate a deck's cards, or after a plan or metric change.
argument-hint: "[slug ...] [key=value ...] | <slug> <card name> [<card name> ...]"
---

# score

The metric lives in the `mtg-toolbox:scorer` agent,
`${CLAUDE_PLUGIN_ROOT}/agents/scorer.md`; the owner tunes it there, this
skill only applies it. Scores are never hand-edited: when one looks wrong,
fix the metric or the deck's `plan.md` and rescore.

Settings and dispatch as the deck-files skill's Dispatch section says.

To rank the decks, dispatch `rankers` `mtg-toolbox:ranker` agents, lettered
A, B, C and on, each prompt giving `<run>` and the letter; they read every
deck's two fact files in `<run>`: combos and counts. When all are
back, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/merge_rankings.py <run>`
merges their `<run>/rankings-<letter>.md` into `<run>/rankings.md` and
prints each deck's criteria the rankers put 4 or more apart. Copy
`<run>/rankings.md` over `rankings.md`.

1. If Moxfield's `updated` may be newer than the list, run
   `mtg-toolbox:sync` first.
2. Make a fresh scratchpad folder `<run>/` and write each deck's two fact
   files into it,
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/facts.py <run> <slug> ...`,
   and check each deck's plan,
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/plan_check.py <slug> ...`,
   which prints each plan card name not in the deck's list.
   When Spellbook is unreachable the run goes on without the combos files.
   If `rankings.md` is missing or has no row for one of the run's decks,
   first rank the decks. Group decks by shared colours (two or three per group). Dispatch
   `scorers` `mtg-toolbox:scorer` agents per group, lettered A, B, C and
   on, each prompt giving `<run>`, the letter, the scorer's own
   `<run>/work-<group>-<letter>/` subfolder, where its finished files land,
   and the group's slugs, each with its bracket from `rankings.md` and its
   combos file.
3. When all of a group are back, per deck
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/merge.py <run> <slug>`. It
   prints the deck's shape line and, with two or more scorers, the count of
   split cards (merge.py's SPLIT apart), listed in `<run>/<slug>-flagged.md`.
4. Copy each deck's merged pair, `<run>/merged/<slug>/`, into
   `output/decks/<slug>/`. Check the shape line merge.py printed for each
   deck against rule 8 of the metric. Then, unless `images` is false, per
   deck `python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/sheet.py <slug>`
   redraws `output/decks/<slug>/changes.png` from its Adds and Cuts tables; a
   deck with neither prints "no adds or cuts" and gets no image. With
   `images` false the report says in a line that changes.png was skipped.
5. If more than one deck was rescored, or the owner asks, run `facts.py`
   on `<run>` with every deck not rescored this run, then rank the decks.

Card names after a slug, `/score <slug> <card name> [<card name> ...]`,
score only those cards for that deck, usually a card just added through
`changes.md`. A card not in the deck's `list.txt` is a candidate, scored as
if added; one missing from `oracle.json` is fetched into it first with
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch_oracle.py "<card name>" ...`,
which reports any name Scryfall does not know. Run steps 2 to 4 for that
deck alone as a group of one, each scorer's prompt also naming the cards,
and merge.py given them after the slug, `merge.py <run> <slug> "<card name>" ...`; it
patches those rows into the deck's `nonlands.md` and `lands.md` (a
candidate's into Adds) instead of rewriting them; a later `/upgrades`
drops a candidate its research does not list. The rankers do not run.

Report: per deck its score from `rankings.md`, the shape line, the 10s and
the split cards in one line ("split: X, Y"), a sign the plan is unclear on
them; anything that moved by 3 or more since the last scoring; the lines
`plan_check.py` printed.
