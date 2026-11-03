---
name: upgrades
description: Research ranked adds and cuts for one or more of your Commander decks, weighting cards released after the deck was built, and write them as the Adds and Cuts tables of output/decks/<slug>/nonlands.md and lands.md. Use when asked for upgrades, new cards, what to cut, or to refresh the adds and cuts lists.
---

# upgrades

Read `settings.json` through `settings.py`
(`python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/settings.py`); dispatch each
agent with `model` only when it differs from the agent's own. Every agent
here runs `run_in_background` in the folder that holds `output/`; its
prompt carries only the per-run inputs named below.

1. Get each deck's `created` and `updated` (the `/sync` fetch returns
   them) and its bracket from `rankings.md`.
2. Make a fresh scratchpad folder `<run>/`. Dispatch one
   `edhtool:researcher` per colour-sharing group of two or three
   decks, so each researches a colour's new cards once, its prompt giving
   `<run>`, `<today>`, `<budget>` (`budget` as `$<n>`, or `none`) and the
   group's decks, each slug with its commander, created and updated dates
   and bracket.
3. Per deck, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/apply.py <run> <slug>`,
   which prints the adds it drops; then
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch-oracle.py`, `apply.py`
   once more per deck so each new add is filed by its type, and
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/sheet.py <slug>`, which
   writes `output/decks/<slug>/changes.png`.

Report: three lines per deck, top adds and top cuts, plus any add that
would change a bracket.
