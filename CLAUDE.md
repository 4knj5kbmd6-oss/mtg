# mtg

Your Commander decks and the tooling around them.

Project words: Moxfield, TCGplayer, Scryfall, Commander, bracket, Game
Changer, fit score, decklist.

## Layout

[README.md](README.md#layout) lays out the repo, the owner's project-wide
files and `output/`. A deck's `output/decks/<slug>/plan.md` is
authoritative: it overrides anything inferred from the list.

## Skills

Procedures are skills in `skills/`, each with its scripts beside it; the
agents they dispatch are in `agents/`: `sync`, `score`, `upgrades`, `cart`,
`judge`.

The repo is the `edhtool` plugin: the skills and agents load from an installed plugin or with
`claude --plugin-dir .`, and run from the folder that holds `output/`.

## Rules

- Results, not analysis. The value of the repo is the
  score on each card and the recommended adds; every generated file is a
  table with one short reason per row and no prose around it. Rankings
  are the table alone. Agents, skills and docs say each thing once.
- Plans are the owner's. Draft changes for their review; add no intent they
  have not stated.
- Agents write to the scratchpad; the orchestrator copies results in.
  Output paths are gitignored, so nothing there is committed; a change to
  a core file is committed as it lands.
- Every landing on `main` bumps the patch number of `version` in
  `.claude-plugin/plugin.json`, so installed copies update; minor and
  major numbers are the owner's.
