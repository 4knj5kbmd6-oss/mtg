# Upgrade research brief

Paths are relative to the mtg repo root, your working directory.

You are recommending updates to the owner's Commander (EDH) decks. Read-only on
the repo; write your output to the scratchpad path named at the end.

## Inputs
- output/decks/<slug>/plan.md: the owner's intended lines, authoritative.
- output/decks/<slug>/list.txt: the list, commander first, then the 99, optional SIDEBOARD block.
- output/data/oracle.json: Scryfall data for every card in every deck (rules text, cost, type,
  colours, Game Changer flag). Read this instead of fetching card by card.
- output/rankings.md: each deck's bracket and its strength relative to the others.
- output/data/tokens.md: tokens the decks make (occasionally relevant).

## Deck dates (Moxfield; "created" is the build date, "updated" the last edit)
| slug | commander | created | updated | bracket |
|---|---|---|---|---|
<fill in from the sync fetch and output/rankings.md>

## What to do, per deck
1. Read the plan, then the list.
2. PRIMARY: find cards released AFTER the deck's created date (and especially after
   its updated date) that improve it. Today is <today>. Use web search to
   establish which Magic sets released between the deck's creation and today
   (Standard sets, Commander precons, Universes Beyond sets, supplemental sets),
   then search each for cards in the deck's colour identity that fit its plan.
   Scryfall search syntax is useful: e.g. `id<=br date>=2025-08-07 o:"..."`.
   Verify every card's rules text and release date on Scryfall before recommending it.
   Do not recommend a card that is already in the deck.
3. SECONDARY: older cards that are clear upgrades the list is missing.
4. Keep the deck at its bracket in output/rankings.md. An add that would push it over (a
   Game Changer past the cap, an infinite combo in a bracket-2 deck, etc.) is still
   listed, and its own Why says so.
5. Give an approximate current price (TCGplayer market) per add. Prefer cheap
   unless the gain is large.
6. A card is in only if you can say what it does for this deck's specific plan.

## Output

Two files per deck, judged independently and never paired, at
<run>/<slug>-adds.md and <run>/<slug>-cuts.md. Each is a title line and a
table, nothing else. A Why cell is one clause of at most about 15 words naming
the card's role and the interaction it joins (or, for a cut, why it falls short).

<slug>-adds.md, exactly 20 adds, ranked best first:

```
# <deck>: top adds (<date>)
Built <created>, last edited <updated>, bracket <n>.

| # | Add | Set (release) | New since built? | Why | ~Price |
|---|---|---|---|---|---|
```

<slug>-cuts.md, the 10 to 15 cards that pull least weight, weakest first,
each judged against the plan and the rest of the list:

```
# <deck>: top cuts (<date>)

| # | Cut | Why it underperforms here |
|---|---|---|
```

Final message: 3 lines per deck (top 3 adds, top 3 cuts), nothing more.
