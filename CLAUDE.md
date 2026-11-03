# mtg

Your Commander decks and the tooling around them.

Project words: Moxfield, TCGplayer, Scryfall, Commander, bracket, Game
Changer, fit score, decklist.

## Layout

Core (tracked): `CLAUDE.md`, `README.md`, the agents in `agents/`
(`scorer.md` holds the 0 to 10 metric the owner tunes), the skills in
`skills/` and the plugin and marketplace manifests in `.claude-plugin/`.

The owner's settings, `settings.json` beside `output/` (gitignored), read
by the skills that dispatch agents or write adds; an absent file or key
takes the default. `scorers`: independent scorers per deck in `score`
(default 3). `model`: the model every dispatched agent runs on (default
`claude-opus-5-5`). `budget`: the highest TCGplayer market price in dollars
an add may carry (default none, no cap).

The owner's output, under `output/` (gitignored):

- `output/decks/moxfield.json`: the owner's Moxfield username and the decks
  synced, `{"user": "<moxfield username>", "decks": {"<id>": "<slug>"}, "seen": ["<id>", ...]}`,
  written by `/sync <username>` with every public Commander deck not yet
  seen and trimmed by hand; a deck deleted from `decks` stays out.
- `output/decks/rankings.md`: the decks in strength order, one table: commander
  (linking to the deck folder), colours, WotC-guideline bracket, Game Changers, one
  line why, Moxfield link.
- `output/decks/<slug>/`: everything about one deck.
  - `list.txt`: the deck as the owner intends it: Moxfield's list with
    `output/changes.md` applied. Card names only ("1 Card Name"), commander
    first, then the 99, optional `SIDEBOARD:` block. No set codes or
    collector numbers.
  - `plan.md`: the owner's statement of the deck's intended lines and
    interactions. Authoritative. Scorers and rankers read it first; it
    overrides anything inferred from the list.
  - `nonlands.md` and `lands.md`, one shape: one score per card sorted
    descending, then the Adds and Cuts tables (recommended adds and cuts,
    judged independently, never paired), then the shape line. A card goes
    to `lands.md` if its front face is a Land.
  - `changes.png`: the earliest-printing image of every add and cut, in four
    bands: nonland adds, nonland cuts, land adds, land cuts.
- `output/restricted.md` (every deck) and `output/decks/<slug>/restricted.md` (one
  deck): card names, one `- Name` line each and nothing else; `upgrades`'
  `apply.py` drops an add named on either.
- `output/changes.md`: the owner's intended swaps not yet made, one table
  (Deck, In, Out, Note) across all decks; `sync` drops a row once Moxfield
  shows it and re-applies the rest to the lists.
  A Note of `unowned` (`unowned, 10 copies` for basics) marks a card to buy,
  possibly already in the list; the row stays until the owner clears it.
- `output/data/`: `oracle.json` (rebuilt by `sync`'s `fetch-oracle.py`,
  each card with its Scryfall rulings), `tokens.md`, and `rules.txt` with
  `rules-index.md` (the Comprehensive Rules and their headings, from
  `judge`'s `fetch-rules.py`).
- `output/carts/`: one report per cart.

## Skills

Procedures are skills in `skills/`, each with its scripts beside it; the
agents they dispatch are in `agents/`:

- `sync`: refresh lists and tokens from Moxfield through the browser pane.
- `score`: independent scorers per deck, median kept, split cards
  reported; optional rankings recompute.
- `upgrades`: ranked adds and cuts per deck, new-since-built weighted.
- `cart`: a shopper agent builds and optimizes a TCGplayer guest cart from
  a list.
- `judge`: the Comprehensive Rules on disk and a judge agent for rules
  questions, citing rule numbers.

The repo is the `commander-deckhand` plugin: the skills and agents load from an installed plugin or with
`claude --plugin-dir .`, and run from the folder that holds `output/`.

## Rules

- Results, not analysis. The value of the repo is the
  score on each card and the recommended adds; every generated file is a
  table with one short reason per row and no prose around it. Rankings
  are the table alone. Briefs, skills and docs say each thing once.
- Scores are never hand-edited. When one looks wrong, fix the metric in
  `agents/scorer.md` or the deck's `plan.md` and rescore.
- Rankings judge strength at a four-player table, not a sum of scores;
  brackets follow WotC's published guidelines, not a Game Changer count.
- Plans are the owner's. Draft changes for their review; add no intent they
  have not stated. Rules facts may be resolved from oracle text.
- Only public, owned decks are exported; theorycraft stays out. Never sign
  in to Moxfield or TCGplayer, never check out.
- Agents write to the scratchpad; the orchestrator copies results in.
  Output paths are gitignored, so nothing there is committed; a change to
  a core file is committed as it lands.
- Every landing on `main` bumps the patch number of `version` in
  `.claude-plugin/plugin.json`, so installed copies update; minor and
  major numbers are the owner's.
