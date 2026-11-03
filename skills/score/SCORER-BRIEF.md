# Scorer brief

Paths are relative to your working directory, the folder that holds output/.

You are one of three independent scorers for a group of Commander decks. Your
scores will be compared with two other scorers' and the median taken, so
score honestly and on your own: do NOT read any existing output/decks/*/nonlands.md or
lands.md beyond the Card columns of their Adds tables, or any other scorer's output in
the scratchpad. Work only in your own subfolder of the scratchpad (named in your
prompt) so you never collide with the other scorers.

Read <scoring> in full and apply the anchors, rules and expected shape
exactly.

FIRST, for each deck, read output/decks/<slug>/plan.md. It is the owner's statement
of the deck's intended lines and interactions and it overrides any plan you
infer from the list. A card the plan names as part of a line is scored on
that line, not on its face value.

Inputs per deck (<slug>):
- output/decks/<slug>/list.txt: the list (commander first, then the 99, optional
  SIDEBOARD block which you do not score).
- output/data/oracle.json: rules text for every card. Read it, do not fetch card by
  card. Use Scryfall only for adds missing from it.
- output/decks/<slug>/nonlands.md and lands.md, the Card columns of their `## Adds` tables
  only: the recommended adds, to be scored as if already in the deck.

A rules question about a card you settle yourself as <plugin>/skills/judge/JUDGE-BRIEF.md
directs, with `python3 <plugin>/skills/judge/card.py "Card Name"` for its oracle text and rulings
and `python3 <plugin>/skills/judge/rule.py` (`--find word ...` to locate rules, a number such as
`702.87` for a rule and its subrules) for the Comprehensive Rules.

Output per deck, exactly this file:
<run>/<slug>-<LETTER>.md
where LETTER is the one in your prompt (A, B or C).

```
# <Deck>: fit scores (<LETTER>)

## Nonlands
| Card | Score | Note |
|---|---|---|
...every nonland card, score descending...

## Lands
| Card | Score | Note |
|---|---|---|
...every land, score descending; basics as one row "Swamp (29)" with the count...

## Adds
| Card | Score | Note |
|---|---|---|
...every card in both Adds tables, score descending...

## Shape
<count at 10 / 8-9 / 5-7 / 4 or below, by card copy>
```

Card names must match the deck file exactly (double-faced cards with both
faces, "Front // Back"). Every card in the list gets a row. Notes are at
most a dozen words naming role and reason.

Final message: per deck, the shape line and the cards you scored 10. Nothing
else.
