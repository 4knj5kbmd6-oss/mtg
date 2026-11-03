---
name: mtg-upgrades
description: Research ranked adds and cuts for one or more of your Commander decks, weighting cards released after the deck was built, and write them as the Adds and Cuts tables of output/decks/<slug>/nonlands.md and lands.md. Use when asked for upgrades, new cards, what to cut, or to refresh the adds and cuts lists.
---

# mtg-upgrades

Adds and cuts are judged independently and never paired. Cards printed
after the deck's build date get priority; everything is verified on
Scryfall; every add carries an approximate TCGplayer price, and an add
that would change the deck's bracket says so in its own row.

1. Get each deck's `createdAtUtc` and `lastUpdatedAtUtc` (the `/mtg-sync`
   fetch returns them) and its bracket from `output/rankings.md`.
2. Copy `BRIEF.md` to a fresh scratchpad folder with the dates table and
   `<today>` filled in. Dispatch one `planner` (`model: claude-opus-5-5`,
   `run_in_background`) per colour-sharing group of two or three decks, so
   each researches a colour's new cards once. Planners have web search;
   they must verify rules text and release date on Scryfall.
3. Per deck, `python3 .claude/skills/mtg-upgrades/apply.py <run> <slug>`
   writes the results into `output/decks/<slug>/nonlands.md` and
   `lands.md`, each card by its type in `output/data/oracle.json`: cuts carry
   their deck score, new adds score `-` until `/mtg-score` scores them as
   part of the deck. Then `python3 .claude/skills/mtg-sync/fetch-oracle.py`
   caches the adds in `output/data/oracle.json` for the scorers.

Report: three lines per deck, top adds and top cuts, plus any add that
would change a bracket.
