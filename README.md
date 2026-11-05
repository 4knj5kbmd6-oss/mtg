# mtg-toolbox

A rules judge and tooling for your Commander decks, run by Claude Code
skills: a 0 to 10 fit score for every card in a deck, ranked adds and cuts, a
strength ranking of your decks with their brackets, and a TCGplayer cart
builder.

## Install

In Claude Code:

```
/plugin marketplace add 4knj5kbmd6-oss/mtg
/plugin install mtg-toolbox
```

Or in one step from a shell:
`claude plugin install mtg-toolbox --marketplace 4knj5kbmd6-oss/mtg`.

The skills read and write `output/` in the folder you open Claude Code in.
They need Python 3.9 or later with Pillow (`pip install pillow`), and
`/sync` and `/cart` need the Claude desktop app's browser pane.

## Judge

```
/judge I reanimate an opponent's creature with Reanimate and later lose the game. What happens to it?
```

> It is exiled, and does not return to its owner. Reanimate put it onto the
> battlefield under your control, so you control it by default, not through
> an effect that ends when you leave; when you lose you leave the game, and
> the objects you still control are exiled.
>
> Rules: 104.5, 800.4a, 110.2
>
> Reanimate ruling: "If you leave the game, the creature you control from
> Reanimate is exiled."

`/judge` needs no decks and no account: it fetches the Comprehensive Rules on
first use and looks up on Scryfall any card it has not seen.

## Your decks

1. `/sync <moxfield username>` adds your public Commander decks to
   `moxfield.json` and writes each deck's `list.txt`.
2. Write each deck's `output/decks/<slug>/plan.md`: the lines the deck means
   to play. A bullet `- **Not cast:** Card, Card` names the cards it cheats
   into play rather than casts; `/mana` leaves them out of its land count.
3. `/score`, then `/upgrades`; `/cart` builds a TCGplayer cart from any list.

**Cost.** Every deck in a `/score` run is read by `scorers` scorers on `model`
(defaults in [`settings.py`](lib/settings.py)), each taking a group of
decks that share colours, and a run of more than one deck ends with one
ranker, as a run starts with one when a deck has no bracket yet. `scorers` and `model` in `settings.json` lower it.

## Settings

`settings.json`, beside `output/`, holds any of these keys. An absent file
or key takes its default from [`settings.py`](lib/settings.py), and
a partial `quota` or `cart` keeps the rest of its default. A `key=value` on
the command line overrides one for that run (`/score budget=50 quota.adds=15`).

| Key | What |
|---|---|
| `scorers` | Scorers per deck |
| `model` | The model every dispatched agent runs on; null: each agent's own |
| `budget` | The highest TCGplayer price in dollars an add may carry |
| `quota` | The adds, land adds and cuts each deck's research lists |
| `universes_beyond` | true: research searches Universes Beyond sets |
| `new_sets` | true: research recommends only cards from the sets released since each deck's last edit, searched exhaustively |
| `cart` | Condition, language, finish and premium per package removed; asked each cart while null |

## changes.md

`changes.md`, beside `output/`, holds your intended swaps not yet made on
Moxfield, one row each. `/sync` re-applies them to each `list.txt` and drops
each row once Moxfield shows it.

```
| Deck | In | Out | Note |
|---|---|---|---|
| <slug> | <card to add> | <card to cut> | |
```

Either card may be blank. A Note of `unowned` keeps the row until you clear
it; `<n> copies` adds n copies of the In card and cuts every copy of the
Out card; `to <n> copies` sets the row's one card, In or Out, to exactly n
copies, 0 cutting it, so basics can be swapped.

## Layout

Your project-wide files, beside `output/` (gitignored):

| Path | What |
|---|---|
| `settings.json` | Your [settings](#settings) |
| `moxfield.json` | Your Moxfield username, the decks synced and each one's created and updated dates, written by `/sync <username>`; a deck you delete from it stays out |
| `changes.md` | Your [intended swaps](#changesmd) not yet made on Moxfield |
| `restricted.md`, `output/decks/<slug>/restricted.md` | Card names, one `- Name` line each, never added: for every deck, and for one deck |
| `rankings.md` | Your decks in strength order: commander, colours, bracket, score (0 to 10, the mean of the six criteria below it), kill turn, Game Changers, why, Moxfield link; then a `Criteria` table of each deck's six scores: speed, consistency, resilience, interaction, ceiling, independence |

Your output, all under `output/` (gitignored):

| Path | What |
|---|---|
| `decks/<slug>/` | `list.txt` (the deck as you intend it: Moxfield's list with `changes.md` applied), `plan.md`, `nonlands.md` and `lands.md` (fit scores with each card's Role, adds, cuts; `nonlands.md` ends with a Roles line tallying the roles), `changes.png` (an image of every add and cut, redrawn by `/score` and `/upgrades`) |
| `data/` | `oracle.json` (Scryfall, with each card's rulings, functional `tags` and EDHREC `salt`) and `tokens.md` |
| `data/variants.json.gz` | Commander Spellbook's combos, fetched again by `/score` once a day old |
| `data/oracle-tags.jsonl.gz`, `data/AtomicCards.json.gz` | Scryfall's oracle tags and MTGJSON's atomic cards, the sources of each card's `tags` and `salt` in `oracle.json`, fetched again by `/sync` when the source is newer |
| `data/rules.txt` | The Comprehensive Rules, for `/judge` |
| `data/scryfall-syntax.md` | Scryfall's search reference, one section per docs page, for `/scryfall` |
| `carts/` | One report per cart |
