---
name: scryfall
description: Build and check a Scryfall search query with a librarian agent given Scryfall's search reference, proving it against the live search; fetch the reference into output/data/scryfall-syntax.md. Use for /scryfall <what to find>, or when the owner asks how to search Scryfall for something.
argument-hint: "<what to find>"
---

# scryfall

Scryfall's search reference is `output/data/scryfall-syntax.md`, one `##`
section per docs page.

Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/settings.py` with the
arguments' `key=value` words for this run's settings. Dispatch every agent
`run_in_background` in the folder that holds `output/`, with `model` only
when it differs from the agent's own; its prompt carries only the per-run
inputs named below.

For `/scryfall <what to find>`:

1. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/scryfall/fetch-syntax.py`; it
   writes the reference from scryfall.com/docs when the file is missing, or
   again with `--refresh`.
2. Dispatch one `mtg-deckhand:librarian`, its prompt giving the request and
   the path `output/data/scryfall-syntax.md`.
3. Give its answer in chat. Nothing else is written to `output/`.
