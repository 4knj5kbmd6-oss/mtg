---
name: mtg-score
description: Score every card in one or more of your Commander decks with the fit-score metric (three independent Opus scorers, median, arbitration), write output/decks/<slug>/scores.md, optionally recompute output/rankings.md. Use when asked to score, rescore or re-evaluate a deck's cards, or after a plan or metric change.
---

# mtg-score

The metric is `scoring.md` at the repo root; the owner tunes it, this skill only
applies it. Scores are never hand-edited: when one looks wrong, fix the
metric or the deck's `plan.md` and rescore.

Inputs per deck: `output/decks/<slug>/list.txt`, `plan.md` (authoritative),
the Card column of the `## Adds` table in `scores.md` (adds are scored
too), `output/data/oracle.json`.

1. If Moxfield's `lastUpdatedAtUtc` may be newer than the list, run
   `/mtg-sync` first.
2. Make a fresh scratchpad folder `<run>/` and copy `SCORER-BRIEF.md` into
   it with `<run>` filled in. Dispatch three `planner` agents per deck
   group (`model: claude-opus-5-5`, `run_in_background`), lettered A, B, C,
   each with its own `work-<group>-<letter>/` subfolder (every scorer in
   the run gets a folder of its own; two sharing one overwrite each
   other's helpers) and a list of its decks with the deck's bracket from
   output/rankings.md. Group decks by shared colours (three or so per
   agent). Scorers must not see each other's output or any existing
   `scores.md` beyond its adds; the brief says so.
3. When all three of a group are back:
   `python3 .claude/skills/mtg-score/merge.py <run> <slug> > <run>/merged/<slug>.md`.
   It takes the median, carries the Adds and Cuts tables over from the
   current `scores.md` with this run's scores, writes `<run>/<slug>-flagged.md` for cards whose
   three scores differ by 3 or more, and prints the deck's shape line and
   flagged count.
4. Flagged cards go to one `planner` arbiter per batch with
   `ARBITER-BRIEF.md`; it writes `<run>/arb-<slug>.json`. Rerun merge with
   the json as the third argument. Batch across decks; most runs flag 0 to
   4 cards in total.
5. Copy each merged file to `output/decks/<slug>/scores.md`. Check the shape line
   merge.py printed for each deck against rule 8 of `scoring.md`.
6. If more than one deck was rescored, or the owner asks, recompute
   `output/rankings.md` with one `planner` using `RANKER-BRIEF.md`; copy the result
   over `output/rankings.md`, regenerate the deck table in `output/decks/README.md` (rank,
   commander, colours, bracket, Moxfield link).

Report: per deck the shape line and the 10s; any arbitration in one line
each; anything that moved by 3 or more since the last scores.md.
