---
name: mana
description: Compute one or more of your Commander decks' mana from the list itself, its land count and curve, the chance of hitting lands on curve, and per colour the land sources beside the sources its most demanding card needs, and show the tables. Use for /mana <slug ...>, or when the owner asks whether a deck has enough lands or sources of a colour.
argument-hint: "<slug> [slug ...]"
---

# mana

The script runs from the folder that holds `output/`; `/score` and
`/upgrades` read the same file through `facts.py`.

For `/mana <slug> [slug ...]`:

1. Make a fresh scratchpad folder `<run>/` and write each deck's mana file
   into it, `python3 ${CLAUDE_PLUGIN_ROOT}/skills/mana/mana.py <run> <slug> ...`.
   It prints any card `oracle.json` lacks, left out of the counts.
2. Show each deck's `<run>/<slug>-mana.md` tables in chat. Nothing is
   written to `output/`.
