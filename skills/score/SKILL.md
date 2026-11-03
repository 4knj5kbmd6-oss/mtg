---
name: score
description: Score every card in one or more of your Commander decks with the fit-score metric (independent scorers, median), write output/decks/<slug>/nonlands.md and lands.md, redraw its changes.png, optionally recompute rankings.md. Use when asked to score, rescore or re-evaluate a deck's cards, or after a plan or metric change.
argument-hint: "[slug ...] [key=value ...] | <slug> <card name> [<card name> ...]"
---

# score

The metric lives in the `mtg-toolbox:scorer` agent,
`${CLAUDE_PLUGIN_ROOT}/agents/scorer.md`; the owner tunes it there, this
skill only applies it. Scores are never hand-edited: when one looks wrong,
fix the metric or the deck's `plan.md` and rescore.

Run `python3 ${CLAUDE_PLUGIN_ROOT}/lib/settings.py` with the
arguments' `key=value` words for this run's settings. Dispatch every agent
`run_in_background` in the folder that holds `output/`, with `model` only
when it differs from the agent's own; its prompt carries only the per-run
inputs named below.

1. If Moxfield's `updated` may be newer than the list, run
   `mtg-toolbox:sync` first.
2. Make a fresh scratchpad folder `<run>/`. Per deck write its two fact
   files, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/combos.py <run> <slug>`
   and `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/mana.py <run> <slug>`.
   When Spellbook is unreachable the run goes on without the combos file.
   Group decks by shared colours (two or three per group). Dispatch
   `scorers` `mtg-toolbox:scorer` agents per group, lettered A, B, C and
   on, each prompt giving `<run>`, the letter, the scorer's own
   `<run>/work-<group>-<letter>/` subfolder and the group's slugs, each with
   its bracket from `rankings.md` and its two fact files.
3. When all of a group are back, per deck
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/merge.py <run> <slug>`. It
   prints the deck's shape line and, with two or more scorers, the count of
   split cards (merge.py's SPLIT apart), listed in `<run>/<slug>-flagged.md`.
4. Copy each deck's merged pair, `<run>/merged/<slug>/`, into
   `output/decks/<slug>/`. Check the shape line merge.py printed for each
   deck against rule 8 of the metric. Then per deck
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/sheet.py <slug>` redraws
   `output/decks/<slug>/changes.png` from its Adds and Cuts tables; a deck
   with neither prints "no adds or cuts" and gets no image.
5. If more than one deck was rescored, or the owner asks, write the two
   fact files into `<run>` for every deck not rescored this run, as in
   step 2, then recompute the rankings with one `mtg-toolbox:ranker`, its
   prompt giving `<run>`; copy `<run>/rankings.md` over `rankings.md`.

Card names after a slug, `/score <slug> <card name> [<card name> ...]`,
score only those cards for that deck, usually a card just added through
`changes.md`. A card not in the deck's `list.txt` is a candidate, scored as
if added; one missing from `oracle.json` is fetched into it first with
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch_oracle.py "<card name>" ...`,
which reports any name Scryfall does not know. Run steps 2 to 4 for that
deck alone, each scorer's prompt also naming the cards. merge.py patches
those rows into the deck's `nonlands.md` and `lands.md` (a candidate's into
Adds) instead of rewriting them; a later `/upgrades` drops a candidate its
research does not list. The ranker does not run.

Report: per deck the shape line, the 10s and the split cards in one line
("split: X, Y"), a sign the plan is unclear on them; anything that moved by
3 or more since the last scoring.
