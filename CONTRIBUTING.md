# Contributing

Pull requests are welcome, and every one gets a review. A fix, a new skill,
a sharper metric, a better word in a doc: if it makes the toolbox better for
someone's decks, open it. Not sure where a change belongs or whether it fits?
Open an issue and ask; a question is a fine first contribution. The steps
below keep a change easy to review and land.

1. **An issue first.** Open a [bug](.github/ISSUE_TEMPLATE/bug.md) or an
   [enhancement](.github/ISSUE_TEMPLATE/enhancement.md) with the request in
   your own words. Before work starts it gains a technical design: the
   files and behaviour that make those words true, and nothing beyond them.
2. **One branch per issue.** Its commit says what changed in a sentence or
   two and ends with `Closes #<n>.`
3. **Scripts take the working directory as the project**, the folder that
   holds `output/`, never their own location. Run the plugin from a clone
   with `claude --plugin-dir <clone>`.
4. **`output/` is the user's.** It is gitignored and never committed.
5. **Green before a pull request:** `python3 -m pytest` and
   `claude plugin validate .` both pass.
6. **Instruction files** (`CLAUDE.md`, `SKILL.md`, agents, this file) state
   each rule as it now stands, with no attribution, dates or history; those
   go in the commit message.

## Layout

| Path | What |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | Layout, skills and rules for Claude Code |
| [`agents/`](agents/) | `scorer` (the fit-score metric, yours to tune), `ranker`, `researcher`, `judge`, `librarian`, `shopper` and `planner` |
| [`skills/`](skills/) | `sync`, `plan`, `score-cards`, `score-deck`, `upgrades`, `cart`, `judge`, `scryfall`, `collection`, `mana` (its method in [`METHOD.md`](skills/mana/METHOD.md)), and `deck-files`, the shared, non-invocable skill |
| [`lib/`](lib/) | The code the scripts share: `net` (Scryfall, Spellbook and Wizards over HTTP), `project` (paths, deck readers, file writes), `tables` (the Markdown tables) and `settings` |
| [`.claude-plugin/`](.claude-plugin/) | Plugin and marketplace manifests |
| [`tests/`](tests/) | The scripts' tests, run on a fixture project |
| [`.github/`](.github/) | Issue templates and the test workflow |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How work is proposed and landed |
| [`LICENSE`](LICENSE) | The licence |
