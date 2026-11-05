# Builder brief: mtg

Implement the mtg change named in your prompt, following this brief and
agents/builder.md. The repo is `/Users/tdienes/git/mtg`, public at
github.com/4knj5kbmd6-oss/mtg-toolbox, with no tester. Requests are GitHub
issues there; the orchestrator fast-forwards `main` to your branch,
amends the patch bump of `version` in `.claude-plugin/plugin.json`
into that landing commit, pushes, and refreshes the owner's installed copy
(`claude plugin marketplace update mtg-toolbox` then
`claude plugin update mtg-toolbox`; the CLI is the binary inside
the Claude desktop app bundle, not on PATH), so your branch is the
hand-off and you never touch the version.

## Setup

Work in the worktree the orchestrator gives you (`isolation: "worktree"`),
never in the main checkout. The merge base for the final squash is
`git merge-base HEAD main`. Scratch files stay in your
own scratchpad folder.

## Building

- Read the repo's CLAUDE.md first: core files versus the gitignored
  `output/` folder (Tom's decks, plans, scores, carts: never edit them
  except where the brief says), and the rules about Moxfield and
  TCGplayer (never sign in, never check out).
- The repo is a Claude Code plugin: skills live in `skills/<name>/` with
  their scripts and agent briefs beside them, the manifest and marketplace
  file in `.claude-plugin/`. A change to a procedure edits the skill, not
  a doc elsewhere. Scripts take the working directory as the project (the
  folder that holds `output/`), never their own location; a worktree gets
  an `output` symlink to the orchestrator's output copy for testing.
- No network calls unless the brief asks: `fetch-oracle.py`, `sheet.py`
  and the sync scripts hit Scryfall and Moxfield.
- Rename or move files with `git mv` so history follows.

## Tests

`python3 -m pytest` must be green before reporting. Also run `python3 -c "import json;
json.load(open('output/data/oracle.json'))"` plus any script you changed, on a
sample input. Check every relative link in the Markdown
you touched still resolves (`grep -o '](\S*)'` against `ls`).

## Report

The builder shape (agents/builder.md). The commit subject says what
changed in one or two present-tense sentences and `Closes #n.` ends the
body when an issue exists. **Branch:** gives the worktree path, the
branch and the squashed commit's hash so the orchestrator can
fast-forward `main`.
