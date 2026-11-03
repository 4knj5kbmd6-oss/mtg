---
name: upgrades
description: Research ranked adds and cuts for one or more of your Commander decks, weighting cards released after the deck was built, and write them as the Adds and Cuts tables of output/decks/<slug>/nonlands.md and lands.md. Use when asked for upgrades, new cards, what to cut, or to refresh the adds and cuts lists.
---

# upgrades

Adds and cuts are judged independently and never paired. Cards printed
after the deck's build date get priority; everything is verified on
Scryfall; every add carries an approximate TCGplayer price, and an add
that would change the deck's bracket says so in its own row. The adds are
the top 20 nonlands plus up to 5 utility lands.

`settings.json`, beside `output/`, sets `model`, the model every agent
here is dispatched on (default `claude-opus-5-5`, the agents' own), and
`budget`, the highest TCGplayer market price in dollars an add may carry
(default none, no cap); an absent file or key takes the default. Every
agent here runs `run_in_background` in the folder that holds `output/`, with
`model` passed only when it differs from the default; its prompt carries
only the per-run inputs named below, since the agent holds its standing
instructions.

1. Get each deck's `createdAtUtc` and `lastUpdatedAtUtc` (the `/sync`
   fetch returns them) and its bracket from `rankings.md`.
2. Make a fresh scratchpad folder `<run>/`. Dispatch one
   `commander-deckhand:researcher` per colour-sharing group of two or three
   decks, so each researches a colour's new cards once, its prompt giving
   `<run>`, `<today>`, `<budget>` (`budget` as `$<n>`, or `none`) and the
   group's decks, each slug with its commander, created and updated dates
   and bracket.
3. Per deck, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/apply.py <run> <slug>`
   writes the results into `output/decks/<slug>/nonlands.md` and
   `lands.md`, each card by its type in `output/data/oracle.json`: cuts carry
   their deck score, new adds score `-` until `/score` scores them as
   part of the deck. It drops, and prints, any add priced above `budget`.
   Then `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch-oracle.py`
   caches the adds in `output/data/oracle.json` for the scorers, and
   `apply.py` runs once more so an add the oracle had not seen is filed by
   its type. Last, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/sheet.py <slug>`
   writes `output/decks/<slug>/changes.png`, the earliest-printing image of
   every add and cut in four bands: nonland adds, nonland cuts, land adds,
   land cuts.

Report: three lines per deck, top adds and top cuts, plus any add that
would change a bracket.
