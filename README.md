# mtg

Tooling for your Commander decks, run by Claude Code skills: a 0 to 10 fit
score for every card in a deck, ranked adds and cuts, a strength ranking of
your decks with their brackets, and a TCGplayer cart builder.

## Install

In Claude Code:

```
/plugin marketplace add 4knj5kbmd6-oss/mtg
/plugin install commander-deckhand
```

The skills read and write `output/` in the folder you open Claude Code in.

## Quick start

1. Clone this repo and open it in Claude Code with `claude --plugin-dir .`.
2. Create `output/decks/moxfield.json` with your Moxfield username and the decks
   you own: `{"user": "<moxfield username>", "decks": {"<id>": "<slug>"}}`
   (or let the first `/sync` create it).
3. Run `/sync` to pull the lists, then write each deck's
   `output/decks/<slug>/plan.md`.
4. Run `/score`, then `/upgrades`; `/cart` builds a cart from any list.

## Layout

Core (tracked):

| Path | What |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Layout, skills and rules for Claude Code |
| [`scoring.md`](scoring.md) | The fit-score metric, yours to tune |
| [`skills/`](skills/) | `sync`, `score`, `upgrades`, `cart`, `judge` |
| [`.claude-plugin/`](.claude-plugin/) | Plugin and marketplace manifests |

Your output, all under `output/` (gitignored):

| Path | What |
|---|---|
| `decks/moxfield.json` | Your Moxfield username and owned decks |
| `decks/README.md` | Deck table: rank, commander, colours, bracket, Moxfield link |
| `decks/<slug>/` | `list.txt` (the deck as you intend it: Moxfield's list with `changes.md` applied), `plan.md`, `nonlands.md` and `lands.md` (fit scores, adds, cuts), `changes.png` (an image of every add and cut: nonland adds, nonland cuts, land adds, land cuts) |
| `rankings.md` | Strength order and brackets |
| `restricted.md`, `decks/<slug>/restricted.md` | Cards, by name or kind, never considered as adds: for every deck, and for one deck |
| `changes.md` | Your intended swaps not yet made on Moxfield; `/sync` re-applies them to each `list.txt` and drops each once Moxfield shows it, except a card noted `unowned`, which stays until you clear the note |
| `data/` | `oracle.json` (Scryfall, with each card's rulings) and `tokens.md` |
| `data/rules.txt`, `data/rules-index.md` | The Comprehensive Rules and their section headings, for `/judge` |
| `carts/` | One report per cart |
