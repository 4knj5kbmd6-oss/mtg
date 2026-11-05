# mtg

Your Commander decks and the tooling around them.

Project words: Moxfield, TCGplayer, Scryfall, Commander, bracket, Game
Changer, fit score, decklist.

## Layout

[CONTRIBUTING.md](CONTRIBUTING.md#layout) lays out the repo and
[README.md](README.md#layout) the owner's project-wide files and `output/`.
A deck's `output/decks/<slug>/plan.md` is
authoritative: it overrides anything inferred from the list.

## Skills

Procedures are skills in `skills/`, each with its scripts beside it,
dispatching the agents in `agents/`. The repo is the `mtg-toolbox` plugin;
[CONTRIBUTING.md](CONTRIBUTING.md) has how to run it from a clone.

## Rules

- Results, not analysis. The value of the repo is the
  score on each card and the recommended adds; every generated file is a
  table with one short reason per row and no prose around it. Rankings
  are the table alone. Agents, skills and docs say each thing once.
- Numbers are computed from the deck, never copied from a published
  table; a method may follow an article, and no file, column or name
  carries an author's name.
- Plans are the owner's. Draft changes for their review; add no intent they
  have not stated.
- Agents write to the scratchpad; the orchestrator copies results in; a
  change to a core file is committed as it lands.
- Every landing on `main` bumps the patch number of `version` in
  `.claude-plugin/plugin.json` inside the landing commit itself, never
  in a commit of its own, so installed copies update; minor and major
  numbers are the owner's.
- A reply ends with its recap alone: no question block, button or
  suggested next action. The owner reads what is open and picks the
  next move; a decision that blocks the work is asked in the body,
  once, as a plain question.
- A card is never called out for serving no line of the plan: good
  value is reason enough to run it.
