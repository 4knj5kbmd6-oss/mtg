---
name: deck-files
description: The deck files the scorer, ranker, researcher, judge and planner agents read, and the scripts that settle a rules question. Preloaded into those agents.
user-invocable: false
---

# Deck files

Paths are relative to the working directory, the folder that holds `output/`.

| File | What |
|---|---|
| `output/decks/<slug>/plan.md` | The owner's plan, in the [shape below](#plan), authoritative: it overrides any plan inferred from the list or from `rankings.md` |
| `output/decks/<slug>/notes.md` | The plan `/plan` replaced, read by the planner only |
| `output/decks/<slug>/list.txt` | The deck as the owner intends it, pending swaps applied: commander first, then the 99, an optional SIDEBOARD block |
| `output/decks/<slug>/nonlands.md`, `lands.md` | Each card's fit score, Role and note, the Adds and Cuts tables and a Shape line; `nonlands.md` ends with a Roles line tallying both files' cards by role |
| `output/data/oracle.json` | Scryfall data for every card in every deck: rules text, cost, type, colour identity, the `game_changer` flag, rulings, `tags` (Scryfall's functional tags), `salt` (EDHREC saltiness, absent when unknown), `price` (USD of the fetched printing: Scryfall's usd, else usd_foil, else usd_etched; absent when Scryfall has none). Read it instead of fetching card by card; Scryfall only for a card missing from it |
| `output/data/brackets.md` | Wizards' Commander Brackets announcement and its updates, one `##` section per article in date order, each with its `Source:` URL |
| `rankings.md` | Beside `output/`: the decks in strength order, each with its bracket and strength score (0 to 100 to one decimal), then a `Criteria` table of each deck's scores on the criteria in `${CLAUDE_PLUGIN_ROOT}/agents/ranker.md`, Speed, Interaction and Card quality, each 1 to 9, the Score the mean of each normalised from 1 to 9 to 100; then a `Speed` table of the two judged axes, Win and Development, each 1 to 9, whose mean is Speed; then a `Card quality` table of its four computed levels, Commander salt, Commander price, 99 salt and 99 price, whose mean is Card quality, and USD, the deck's summed price in whole dollars; then a `Ledger` table naming the cards behind each deck's scores |
| `<run>/<slug>-combos.md` | Commander Spellbook's combos, its Included and Almost included tables with each combo's bracket tag and salt, and the cards it flags as mass land denial or extra turns. Spellbook knows only catalogued combos, so a plan's own kill may show nothing there |
| `<run>/<slug>-counts.md` | Per category (recursion, protection, answers and of those the instant-speed ones, counters, removal, creature and noncreature removal with the wipes that hit them, wipes) the count of the list's cards that `oracle.json`'s tags put in it, and their names; a card the tags miss is absent. Interaction is computed from these rows by the Interaction table in merge_rankings.py. A `Game Changers` row: the count and names of the list's cards whose `oracle.json` entry has `game_changer`, the SIDEBOARD block left out, or `-`. Four final rows, each with its Count a level from 1 to 9, rounded half up and held there, whose mean is Card quality, from each card's `salt` and `price`, the commanders apart from the 99 (the rest of the list), a card with no value adding nothing: `Commander salt`, the commanders' salts summed, and `Commander price`, their prices summed, each with Cards the sum and every commander with its value (`sum 0.75; Tymna the Weaver 0.45; Kraum, Ludevic's Opus 0.30`); `99 salt`, the mean over the 99's copies, lands under 0.5 left out, Cards the mean and its cards at 2.0 or more, saltiest first (`mean 0.62 over 85 cards; Rhystic Study 2.80; The One Ring 2.50`); `99 price`, the 99's prices summed per copy, Cards the sum and its cards at $20 or more, priciest first (`sum $1834.20 over 97 cards; The One Ring $62.00`). A salt level is `1 + 8 * (salt - 0.3) / 0.6`; the 99's price level `1 + 8 * ln(usd / 125) / ln(32)` (125 dollars is 1, 4,000 is 9), the commanders' `1 + 8 * log10(usd) / 2` (1 dollar is 1, 100 is 9) |

## Plan

```
# <Commander>: plan

- **Win:** <name>: <role> + <role> (+ <role>). <One sentence: how it closes.>
- **Commander:** <one sentence: its job in the lines above>
- **cEDH:** yes
- **Not cast:** Card; Card
- **Restriction:** <for research only; the ranker does not read it>
```

Win bullets are the plan. A line joins its roles with `+`; a role is one
card, or a role name with the cards that fill it in brackets, separated by
`;` since card names hold commas. A combo is a line whose every role has one
card; a fair deck has several cards per role. Not cast names the cards the
deck cheats into play rather than casts. cEDH, an optional line, says the
deck is built for the cEDH metagame, the owner's call: only such a deck is
bracket 5. A plan is a few Win lines, each one sentence beside its roles;
names in brackets are free.
Every card named must be in `list.txt`, which
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/plan_check.py <slug> ...` checks.

```
- **Win:** Drain: Arabella, Abandoned Doll + amplifier (Delney, Streetwise Lookout; Windcrag Siege; Furnace of Rath) + token board (Krenko, Tin Street Kingpin; Legion Warboss). Each attack drains per small creature, amplified.
```

## Dispatch

A skill that dispatches agents runs `python3 ${CLAUDE_PLUGIN_ROOT}/lib/settings.py`
with its arguments' `key=value` words for the run's settings, and dispatches
every agent `run_in_background` in the folder that holds `output/`, with
`model` the agent's entry in `models`; its prompt carries only the per-run
inputs the skill names.

## Rules questions

Settle one from the cards' oracle text, their official rulings and the
Comprehensive Rules, which govern:

- `python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/rule.py`: `702.87` prints a rule
  with its subrules, `--find word ...` lists the rules holding every word,
  `--glossary term` prints a glossary entry;
- `python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/card.py "Card Name"` prints a
  card's oracle text and rulings.
