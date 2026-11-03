---
name: sync
description: Refresh your owned Commander decks from Moxfield into output/decks/<slug>/list.txt, regenerate output/data/tokens.md and output/data/oracle.json; /sync <moxfield username> picks up every public deck, and a pasted decklist or .txt export imports a deck with no Moxfield. Use when asked to sync, refresh, re-export or pull decks from Moxfield, to import a decklist, or before scoring a deck Moxfield says was edited since the last export.
---

# sync

Moxfield blocks curl (Cloudflare 403), so every call goes through the
built-in browser pane from page context. Decks are exported as card names
only; maybeboards never. `moxfield.json`, beside `output/`, is the single list of
Moxfield decks synced:
`{"user": "<moxfield username>", "decks": {"<id>": "<slug>"}, "seen": ["<id>", ...]}`.
Each sync adds the user's public Commander decks not in `seen`, so a deck
the owner deletes from `decks` by hand stays out.

`/sync <username>` sets the user; `/sync` alone takes it from
`moxfield.json`, and with neither, ask the owner for it.

1. `navigate` to `https://moxfield.com/users/<user>` and wait about 10 s
   for the app to render. If the pane shows Cloudflare's check instead,
   ask the owner to pass it there, then go on. Paste the user and the keys
   of `decks` into `fetch.js` and run it with the javascript tool. It lists
   the user's decks and returns, per deck: name, `createdAtUtc`,
   `lastUpdatedAtUtc`, commanders, mainboard, sideboard and the Tokens-tab
   list. The result is large; it lands in a tool-results file. Save its
   text to the scratchpad as `mox.json`.
2. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/sync.py <mox.json>`, run
   from the folder that holds `output/`, adds each new public Commander
   deck to `moxfield.json` with a slug from its name and prints it as
   `added: <slug> (<id>)`. It rewrites every `output/decks/<slug>/list.txt`
   and `output/data/tokens.md` from the dump, removes every row of
   `changes.md` the dump shows landed (In card in the deck or In
   blank, Out card gone or Out blank) and not noted `unowned`, prints it as
   `landed: <deck> <In> for <Out>`, then runs `apply-changes.py`, which
   applies the rows left so each list is the deck as the owner intends it
   again, moves each applied add's row from Adds to Cards and drops each
   applied cut's rows, and prints a line per deck: cards in, cards out. An
   Out row takes one copy unless its Note says `n copies`, so a basic cut
   by count is applied once per sync, not on a manual rerun. Then it prints
   a diff summary.
   A deck that came back as Cloudflare's challenge page or anything else
   but deck data is left as it was, with a `blocked:` line saying so;
   `tokens.md` then stays as it was too, and the last line names every
   deck not refreshed. Opening moxfield.com in the pane, passing the check
   and rerunning `/sync` clears it.
3. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch-oracle.py` rebuilds
   `output/data/oracle.json` from Scryfall, each card with its rulings.

For each `added:` deck create `output/decks/<slug>/` with an empty
`plan.md`.

With no Moxfield, the owner pastes a decklist or names a `.txt` export
(Moxfield, Archidekt, MTGO or Arena). Save a paste to the scratchpad, run
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/import.py <slug> <file>` from
the folder that holds `output/`, which writes `output/decks/<slug>/list.txt`
and prints the card count and every line it could not parse, then
`fetch-oracle.py`. A deck imported this way has no `moxfield.json` entry,
and the Moxfield pass leaves it alone.

Report in a line per changed deck: cards in, cards out; then the added
decks, the landed changes and any blocked deck `sync.py` printed. A deck
whose `lastUpdatedAtUtc` is newer than the modification date of
`output/decks/<slug>/nonlands.md` (`stat -f %Sm -t %F <file>` on macOS,
`date -r <file> +%F` on Linux) needs rescoring (`/score`); say so, do not
start it unasked.
