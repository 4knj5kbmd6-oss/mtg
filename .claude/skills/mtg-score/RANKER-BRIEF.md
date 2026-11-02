# Ranker brief

Paths are relative to the mtg repo root, your working directory.

Recompute the strength ranking of the owner's Commander decks. Inputs:
output/decks/*/list.txt, output/decks/*/plan.md (authoritative on what each deck is trying
to do), output/decks/*/scores.md (per-card fit scores and notes, evidence about card
quality), output/data/oracle.json (rules text and the game_changer flag), and the
current output/rankings.md (prior opinion, not binding).

Deck power does not correspond to the fit scores. Rank on strength in a
four-player game: speed to the win, consistency (tutors, redundancy, card
flow), resilience, interaction quantity and quality, ceiling versus typical
game, and single-card dependence.

Brackets follow Wizards of the Coast's official Commander Brackets
guidelines, not a Game Changer count: fetch the current text (the beta
announcement and every update on magic.wizards.com) and the current Game
Changers list, and apply the full criteria (bracket intent, how early and
reliably the deck wins, two-card infinites and when they come online, tutor
density, mass land denial, chained extra turns, Game Changers, optimization
level).

Output to <run>/rankings.md, exactly this shape, nothing else:

```
# Deck rankings

Strength at a four-player table, strongest first. Bracket is the official
Commander bracket under [Wizards' guidelines](<link to the current update>);
"top" and "low" mark where a deck sits within it.

| # | Commander | Bracket | Why |
|---|---|---|---|
...one row per deck; Why is one line...

## Game Changers

| Deck | Cards |
|---|---|
...one row per deck that has any, then "All others | none"...
```

No deck slugs. Final message: the table.
