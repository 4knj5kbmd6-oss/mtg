---
name: deck-files
description: The deck files the scorer, ranker, researcher and judge agents read, and the scripts that settle a rules question. Preloaded into those agents.
user-invocable: false
---

# Deck files

Paths are relative to the working directory, the folder that holds `output/`.

| File | What |
|---|---|
| `output/decks/<slug>/plan.md` | The owner's intended lines, authoritative: it overrides any plan inferred from the list or from `rankings.md` |
| `output/decks/<slug>/list.txt` | The deck as the owner intends it, pending swaps applied: commander first, then the 99, an optional SIDEBOARD block |
| `output/data/oracle.json` | Scryfall data for every card in every deck: rules text, cost, type, colour identity, the `game_changer` flag, rulings. Read it instead of fetching card by card; Scryfall only for a card missing from it |
| `rankings.md` | Beside `output/`: each deck's bracket and its strength relative to the others |
| `<run>/<slug>-combos.md` | Commander Spellbook's combos, its Included and Almost included tables, and the cards it flags as mass land denial or extra turns. Spellbook knows only catalogued combos, so a plan's own kill may show nothing there |
| `<run>/<slug>-mana.md` | Land count, curve, colour sources against pips |

## Rules questions

Settle one from the cards' oracle text, their official rulings and the
Comprehensive Rules, which govern:

- `python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/rule.py`: `702.87` prints a rule
  with its subrules, `--find word ...` lists the rules holding every word,
  `--glossary term` prints a glossary entry;
- `python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/card.py "Card Name"` prints a
  card's oracle text and rulings.
