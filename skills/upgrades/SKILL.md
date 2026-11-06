---
name: upgrades
description: Research ranked adds and cuts for one or more of your Commander decks, from the whole card pool by fit and price or, with new_sets=true, only from the sets released since each deck's last edit, and write them as the Adds and Cuts tables of output/decks/<slug>/nonlands.md and lands.md, each add scored. Use when asked for upgrades, new cards, what to cut, or to refresh the adds and cuts lists.
argument-hint: "[slug ...] [key=value ...]"
---

# upgrades

Settings and dispatch as the deck-files skill's Dispatch section says.

1. Make a fresh scratchpad folder `<run>/` and write each deck's two fact
   files into it,
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/facts.py <run> <slug> ...`.
   Get each deck's `created` and `updated` from `dates` in
   `moxfield.json`; report each deck with no dates there, its research
   runs with the dates unknown. Get each deck's bracket from
   `rankings.md`; if it is missing or has no row for one of the run's
   decks, first rank the decks as
   `${CLAUDE_PLUGIN_ROOT}/skills/score/SKILL.md` ranks them.
2. Dispatch one `mtg-toolbox:researcher` per colour-sharing group of two
   or three decks, so each researches a colour's new cards once, its prompt giving
   `<run>`, `<today>`, `<budget>` (`budget` as `$<n>`, or `none`),
   `<quota>`, `<universes_beyond>` and `<new_sets>` as `settings.py` prints
   them, and the
   group's decks, each slug with its commander, created and updated dates,
   bracket and combos file.
3. Per deck, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/apply.py <run> <slug>`,
   which prints the adds it drops; then
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch_oracle.py` and `apply.py`
   once more per deck so each new add is filed by its type. Then score each
   deck's adds, the names `python3 ${CLAUDE_PLUGIN_ROOT}/lib/tables.py <slug>`
   prints, as the card names paragraph of
   `${CLAUDE_PLUGIN_ROOT}/skills/score/SKILL.md` scores candidates, its steps
   2 to 4 in this `<run>`: `scorers` `mtg-toolbox:scorer` agents per deck,
   each with its own `<run>/work-<slug>-<letter>/` subfolder, the deck's
   bracket and combos file and those names; then `merge.py <run> <slug>`
   given the names, which patches each Adds row's Score, the merged pair
   copied in and changes.png drawn after, so every add on it carries its
   score.

Report: three lines per deck, top adds with their scores and top cuts,
plus any add that would change a bracket.
