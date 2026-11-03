# Contributing

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
6. **Instruction files** (`CLAUDE.md`, `SKILL.md`, briefs, this file) state
   each rule as it now stands, with no attribution, dates or history; those
   go in the commit message.
