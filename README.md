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
   `moxfield.json` and writes each deck's `list.txt`. A deck
   Moxfield answers with Cloudflare's check is reported and left as it was;
   pass the check in the browser pane and run `/sync` again. With no
   Moxfield, paste a decklist or name a `.txt` export (Moxfield, Archidekt,
   MTGO or Arena) and ask to import it.
2. Write each deck's `output/decks/<slug>/plan.md`: the lines the deck means
   to play.
3. `/score`, then `/upgrades`; `/cart` builds a TCGplayer cart from any list.
   Both `/score` and `/upgrades` first compute two fact files per deck for
   their agents: its combos from Commander Spellbook, and its mana (sources
   against pips, land count, curve).

**Cost.** Every deck in a `/score` run is read by `scorers` scorers on `model`
(defaults in [`settings.py`](skills/score/settings.py)), each taking a group of
decks that share colours, and a run of more than one deck ends with one
ranker. `scorers` and `model` in `settings.json` lower it.

## Layout

Core (tracked):

| Path | What |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Layout, skills and rules for Claude Code |
| [`agents/`](agents/) | `scorer` (the fit-score metric, yours to tune), `ranker`, `researcher`, `judge`, `librarian` and `shopper` |
| [`skills/`](skills/) | `sync`, `score`, `upgrades`, `cart`, `judge`, `scryfall` |
| [`.claude-plugin/`](.claude-plugin/) | Plugin and marketplace manifests |
| [`tests/`](tests/) | The scripts' tests, run on a fixture project |
| [`.github/`](.github/) | Issue templates and the test workflow |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How work is proposed and landed |
| [`LICENSE`](LICENSE) | The licence |

Your project-wide files, beside `output/` (gitignored):

| Path | What |
|---|---|
| `settings.json` | `scorers` per deck, `model` every dispatched agent runs on, null: each agent's own, `budget`: the highest TCGplayer price in dollars an add may carry, `quota`: the adds, land adds and cuts each deck's research lists, `universes_beyond` (true: research searches Universes Beyond sets), `new_sets` (true: research recommends only cards from the sets released since each deck's last edit, searched exhaustively), `cart`: condition, language, finish and premium per package removed (asked each cart while null); an absent file or key takes its default from [`settings.py`](skills/score/settings.py), and a partial `quota` or `cart` keeps the rest of its default; a `key=value` on the command line overrides one for that run (`/score budget=50 quota.adds=15`) |
| `moxfield.json` | Your Moxfield username and the decks synced, written by `/sync <username>`; a deck you delete from it stays out |
| `changes.md` | Your intended swaps not yet made on Moxfield; `/sync` re-applies them to each `list.txt` and drops each once Moxfield shows it, except a card noted `unowned`, which stays until you clear the note |
| `restricted.md`, `output/decks/<slug>/restricted.md` | Card names, one `- Name` line each, never added: for every deck, and for one deck |
| `rankings.md` | Your decks in strength order: commander, colours, bracket, Game Changers, why, Moxfield link |

Your output, all under `output/` (gitignored):

| Path | What |
|---|---|
| `decks/<slug>/` | `list.txt` (the deck as you intend it: Moxfield's list with `changes.md` applied), `plan.md`, `nonlands.md` and `lands.md` (fit scores, adds, cuts), `changes.png` (an image of every add and cut, redrawn by `/score` and `/upgrades`) |
| `data/` | `oracle.json` (Scryfall, with each card's rulings) and `tokens.md` |
| `data/rules.txt` | The Comprehensive Rules, for `/judge` |
| `data/scryfall-syntax.md` | Scryfall's search reference, one section per docs page, for `/scryfall` |
| `carts/` | One report per cart |
