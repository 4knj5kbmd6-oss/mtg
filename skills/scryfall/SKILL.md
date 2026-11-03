---
name: scryfall
description: Build and check a Scryfall search query with a librarian agent given Scryfall's search reference, proving it against the live search; fetch the reference into output/data/scryfall-syntax.md. Use for /scryfall <what to find>, or when the owner asks how to search Scryfall for something.
argument-hint: "<what to find>"
---

# scryfall

The skill builds Scryfall queries for the owner. Scryfall's search reference
is `output/data/scryfall-syntax.md`, one `##` section per docs page. The
scripts run from the folder that holds `output/`, as
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/scryfall/<script>`:

- `fetch-syntax.py` downloads the search syntax, regular expressions, API
  overview and cards/search, cards/named and cards/autocomplete pages from
  scryfall.com/docs and writes the reference, less the API page's honeypot
  paragraph for AI agents; it downloads only when the
  file is missing, or again with `--refresh`.
- `search.py "<query>"` prints the query's count and its first 20 cards'
  names and type lines, or Scryfall's error, and Scryfall's warnings.

For `/scryfall <what to find>`:

1. If `output/data/scryfall-syntax.md` is missing, run `fetch-syntax.py`.
2. Read `settings.json` through `settings.py`
   (`python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/settings.py`), passing it
   every `key=value` word of the arguments, which overrides that setting
   for this run; dispatch each agent with `model` only when it differs
   from the agent's own. Dispatch one `mtg-deckhand:librarian`,
   `run_in_background` in the folder that holds `output/`, its prompt
   giving the request and the path `output/data/scryfall-syntax.md`.
3. Give its answer in chat. Nothing else is written to `output/`.
