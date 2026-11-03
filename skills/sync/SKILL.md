---
name: sync
description: Refresh your owned Commander decks from Moxfield into output/decks/<slug>/list.txt, regenerate output/data/tokens.md and output/data/oracle.json; /sync <moxfield username> picks up every public deck, and a pasted decklist or .txt export imports a deck with no Moxfield. Use when asked to sync, refresh, re-export or pull decks from Moxfield, to import a decklist, or before scoring a deck Moxfield says was edited since the last export.
argument-hint: "[moxfield username]"
---

# sync

Moxfield blocks curl (Cloudflare 403), so every call goes through the
built-in browser pane from page context. Only public, owned decks are
exported; theorycraft stays out. Never sign in to Moxfield. Decks are
exported as card names only; maybeboards never. `moxfield.json`, beside
`output/`, is the single list of Moxfield decks synced:
`{"user": "<moxfield username>", "decks": {"<id>": "<slug>"}, "seen": ["<id>", ...],
"dates": {"<id>": {"created": "<YYYY-MM-DD>", "updated": "<YYYY-MM-DD>"}}}`.

Every script here runs from the folder that holds `output/`.

`/sync <username>` sets the user; `/sync` alone takes it from
`moxfield.json`, and with neither, ask the owner for it.

1. `navigate` to `https://moxfield.com/users/<user>` and wait about 10 s
   for the app to render. If the pane shows Cloudflare's check instead,
   ask the owner to pass it there, then go on. Paste the user and the keys
   of `decks` into `fetch.js` and run it with the javascript tool. It lists
   the user's decks and returns, per deck: name, `created`, `updated`,
   commanders, mainboard, sideboard and the Tokens-tab list. The result is
   large; it lands in a tool-results file. Save its text to the scratchpad
   as `mox.json`.
2. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/sync.py <mox.json>` prints
   `added: <slug> (<id>)` per new deck, `landed: <deck> <In> for <Out>` per
   row of `changes.md` it drops, a line per changed deck (cards in, cards
   out), `rescore: <slug>` per deck whose list changed, and a `blocked:`
   line per deck left as it was, the last line naming every deck not
   refreshed.
3. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch_oracle.py` rebuilds
   `output/data/oracle.json` from Scryfall, each card with its rulings.

For each `added:` deck write an empty `output/decks/<slug>/plan.md`.

With no Moxfield, the owner pastes a decklist or names a `.txt` export
(Moxfield, Archidekt, MTGO or Arena). Save a paste to the scratchpad, run
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/import.py <slug> <file>`, which
writes `output/decks/<slug>/list.txt` and prints the card count and every
line it could not parse, then `fetch_oracle.py`. A deck imported this way
has no `moxfield.json` entry, and the Moxfield pass leaves it alone.

Report in a line per changed deck: cards in, cards out; then the added
decks, the landed changes and any blocked deck `sync.py` printed. A
`rescore:` deck needs rescoring (`/score`); say so, do not start it
unasked.
