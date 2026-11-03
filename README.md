# commander-deckhand

A rules judge and tooling for your Commander decks, run by Claude Code
skills: a 0 to 10 fit score for every card in a deck, ranked adds and cuts, a
strength ranking of your decks with their brackets, and a TCGplayer cart
builder.

## Install

In Claude Code:

```
/plugin marketplace add 4knj5kbmd6-oss/mtg
/plugin install commander-deckhand
```

Or in one step from a shell:
`claude plugin install commander-deckhand --marketplace 4knj5kbmd6-oss/mtg`.

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
   `output/decks/moxfield.json` and writes each deck's `list.txt`. A deck
   Moxfield answers with Cloudflare's check is reported and left as it was;
   pass the check in the browser pane and run `/sync` again. With no
   Moxfield, paste a decklist or name a `.txt` export (Moxfield, Archidekt,
   MTGO or Arena) and ask to import it; `import.py` writes its `list.txt`.
2. Write each deck's `output/decks/<slug>/plan.md`: the lines the deck means
   to play.
3. `/score`, then `/upgrades`; `/cart` builds a TCGplayer cart from any list.

**Cost.** At the defaults every deck in a `/score` run is read by three Opus
scorers, each taking a group of two or three decks that share colours; cards
the scorers split on go to one arbiter per batch, and a run of more than one
deck ends with one ranker. `scorers` and `model` in `output/settings.json`
lower it.

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
| `settings.json` | `scorers` per deck (default 3), `model` every dispatched agent runs on (default `claude-opus-5-5`), `budget`: the highest TCGplayer price in dollars an add may carry (default none); an absent file or key takes the default |
| `decks/moxfield.json` | Your Moxfield username and the decks synced, written by `/sync <username>`; a deck you delete from it stays out |
| `decks/rankings.md` | Your decks in strength order: commander, colours, bracket, Game Changers, why, Moxfield link |
| `decks/<slug>/` | `list.txt` (the deck as you intend it: Moxfield's list with `changes.md` applied), `plan.md`, `nonlands.md` and `lands.md` (fit scores, adds, cuts), `changes.png` (an image of every add and cut: nonland adds, nonland cuts, land adds, land cuts) |
| `restricted.md`, `decks/<slug>/restricted.md` | Card names, one `- Name` line each, never added: for every deck, and for one deck |
| `changes.md` | Your intended swaps not yet made on Moxfield; `/sync` re-applies them to each `list.txt` and drops each once Moxfield shows it, except a card noted `unowned`, which stays until you clear the note |
| `data/` | `oracle.json` (Scryfall, with each card's rulings) and `tokens.md` |
| `data/rules.txt`, `data/rules-index.md` | The Comprehensive Rules and their section headings, for `/judge` |
| `carts/` | One report per cart |

## Contributing

Work starts as an issue: a [bug](.github/ISSUE_TEMPLATE/bug.md) or an
[enhancement](.github/ISSUE_TEMPLATE/enhancement.md).
[CONTRIBUTING.md](CONTRIBUTING.md) has the flow; `python3 -m pytest` and
`claude plugin validate .` pass before a pull request.
