---
name: sync
description: Refresh your owned Commander decks from Moxfield into output/decks/<slug>/list.txt, regenerate output/data/tokens.md and output/data/oracle.json. Use when asked to sync, refresh, re-export or pull decks from Moxfield, or before scoring a deck Moxfield says was edited since the last export.
---

# sync

Moxfield blocks curl (Cloudflare 403), so every call goes through the
built-in browser pane from page context. Only decks the owner physically
owns are exported, as card names only; maybeboards never.
`output/decks/moxfield.json` is the single list of those decks:
`{"user": "<moxfield username>", "decks": {"<id>": "<slug>"}}`.

The first run creates it: ask the owner for their Moxfield username, then
follow the new-deck steps below for every deck they name as owned.

1. `navigate` to `https://moxfield.com/users/<user>` and wait about 10 s
   for the app to render. Paste the keys of `decks` into `fetch.js`
   and run it with the javascript tool. It returns, per deck: name,
   `createdAtUtc`, `lastUpdatedAtUtc`, commanders, mainboard, sideboard and
   the Tokens-tab list. The result is large; it lands in a tool-results
   file. Save its text to the scratchpad as `mox.json`.
2. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/sync.py <mox.json>`, run
   from the folder that holds `output/`, rewrites every `output/decks/<slug>/list.txt` and `output/data/tokens.md`
   from the dump, removes every row of `output/changes.md` the dump shows
   landed (In card in the deck or In blank, Out card gone or Out blank) and
   not noted `unowned`, prints it as `landed: <deck> <In> for <Out>`, then
   runs `apply-changes.py`, which applies the rows left so each list is the
   deck as the owner intends it again, moves each applied add's row from
   Adds to Cards and drops each applied cut's rows, and prints a line per
   deck: cards in, cards out. An Out row takes one copy unless its Note
   says `n copies`, so a basic cut by count is applied once per sync, not
   on a manual rerun. Last it prints a diff summary.
3. `python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch-oracle.py` rebuilds
   `output/data/oracle.json` from Scryfall, each card with its rulings.

Only when the owner names a new deck as owned, run `collect.js` on the
profile page first to list their deck ids (it clicks "View More"), add the
new id and slug to `decks`, and create `output/decks/<slug>/` with an empty
`plan.md`.

Report in a line per changed deck: cards in, cards out; then the landed
changes `sync.py` printed. A deck whose `lastUpdatedAtUtc` is newer than
the modification date of `output/decks/<slug>/nonlands.md`
(`stat -f %Sm -t %F <file>` on macOS, `date -r <file> +%F` on Linux)
needs rescoring (`/score`); say so, do not start it unasked.
