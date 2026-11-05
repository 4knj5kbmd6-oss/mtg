---
name: collection
description: Keep each card of collection.md, the cards you own and how many copies, cached locally, its image in output/data/images/ and its oracle text in output/data/oracle.json, each downloaded once; /collection decks first adds every card of your decks the collection lacks at 1 copy. Use for /collection, /collection decks, or when the owner asks to record or cache the cards they own.
argument-hint: "[decks]"
---

# collection

`collection.md`, beside `output/`, is the owner's table `| Card | Copies |`,
one row per owned card.

- `/collection`: run
  `python3 ${CLAUDE_PLUGIN_ROOT}/skills/collection/collection.py` from the
  folder that holds `output/`.
- `/collection decks`: the same with `decks` after it, which first adds every
  deck card the collection lacks.

Report: the lines it prints.
