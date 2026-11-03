---
name: upgrades
description: Research ranked adds and cuts for one or more of your Commander decks, from the whole card pool by fit and price or, with new_sets=true, only from the sets released since each deck's last edit, and write them as the Adds and Cuts tables of output/decks/<slug>/nonlands.md and lands.md. Use when asked for upgrades, new cards, what to cut, or to refresh the adds and cuts lists.
argument-hint: "[slug ...] [key=value ...]"
---

# upgrades

Run `python3 ${CLAUDE_PLUGIN_ROOT}/lib/settings.py` with the
arguments' `key=value` words for this run's settings. Dispatch every agent
`run_in_background` in the folder that holds `output/`, with `model` only
when it differs from the agent's own; its prompt carries only the per-run
inputs named below.

1. Get each deck's `created` and `updated` (run `fetch.js` as in `/sync`
   step 1 when this session has no fetch result) and its bracket from
   `rankings.md`.
2. Make a fresh scratchpad folder `<run>/` and write each deck's two fact
   files into it, as in `/score` step 2. Dispatch one
   `mtg-toolbox:researcher` per colour-sharing group of two or three
   decks, so each researches a colour's new cards once, its prompt giving
   `<run>`, `<today>`, `<budget>` (`budget` as `$<n>`, or `none`),
   `<quota>`, `<universes_beyond>` and `<new_sets>` as `settings.py` prints
   them, and the
   group's decks, each slug with its commander, created and updated dates,
   bracket and two fact files.
3. Per deck, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/apply.py <run> <slug>`,
   which prints the adds it drops; then
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch_oracle.py`, `apply.py`
   once more per deck so each new add is filed by its type, and
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/sheet.py <slug>`, which
   writes `output/decks/<slug>/changes.png`.

Report: three lines per deck, top adds and top cuts, plus any add that
would change a bracket.
