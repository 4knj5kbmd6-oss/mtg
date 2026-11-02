# mtg

Your Commander decks and the tooling around them.

Project words: Moxfield, TCGplayer, Scryfall, Commander, bracket, Game
Changer, fit score, decklist.

## Layout

Core (tracked): `CLAUDE.md`, `README.md`, `scoring.md` (the 0 to 10 metric
the owner tunes) and the skills in `.claude/skills/`.

The owner's output (gitignored; may be symlinks into a private repo):

- `decks/moxfield.json`: the owner's Moxfield username and owned decks,
  `{"user": "<moxfield username>", "decks": {"<id>": "<slug>"}}`.
- `decks/README.md`: the deck table (rank, commander, colours, bracket,
  Moxfield link).
- `decks/<slug>/`: everything about one deck.
  - `list.txt`: card names only ("1 Card Name"), commander first, then the
    99, optional `SIDEBOARD:` block. No set codes or collector numbers.
  - `plan.md`: the owner's statement of the deck's intended lines and
    interactions. Authoritative. Scorers and rankers read it first; it
    overrides anything inferred from the list.
  - `scores.md`: one score per card plus the recommended adds, nonlands and
    lands in separate tables sorted descending.
  - `adds.md`, `cuts.md`: ranked adds and cuts, judged independently, never
    paired.
- `rankings.md`: strength order and WotC-guideline brackets.
- `data/`: `oracle.json` (rebuilt by mtg-sync's `fetch-oracle.py`) and
  `tokens.md`.
- `carts/`: one report per cart.

## Skills

Procedures are skills in `.claude/skills/`, each with its scripts and agent
briefs beside it:

- `mtg-sync`: refresh lists and tokens from Moxfield through the browser pane.
- `mtg-score`: three independent Opus scorers per deck, median, arbitration,
  one score kept; optional rankings recompute.
- `mtg-upgrades`: ranked adds and cuts per deck, new-since-built weighted.
- `tcg-cart`: build and optimize a TCGplayer guest cart from a list.

## Rules

- Results, not analysis. The value of the repo is the
  score on each card and the recommended adds; every generated file is a
  table with one short reason per row and no prose around it. Rankings
  are the table alone. Briefs, skills and docs say each thing once.
- Scores are never hand-edited. When one looks wrong, fix `scoring.md` or
  the deck's `plan.md` and rescore.
- Rankings judge strength at a four-player table, not a sum of scores;
  brackets follow WotC's published guidelines, not a Game Changer count.
- Plans are the owner's. Draft changes for their review; add no intent they
  have not stated. Rules facts may be resolved from oracle text.
- Only public, owned decks are exported; theorycraft stays out. Never sign
  in to Moxfield or TCGplayer, never check out.
- Agents write to the scratchpad; the orchestrator copies results in.
  Output paths are gitignored, so nothing there is committed; a change to
  a core file is committed as it lands.
