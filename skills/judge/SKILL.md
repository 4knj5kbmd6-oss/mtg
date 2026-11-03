---
name: judge
description: Answer a Magic rules question with a judge agent given the named cards' oracle text and Scryfall rulings and the matching Comprehensive Rules, citing the rule numbers; fetch the Comprehensive Rules into output/data/rules.txt. Use for /judge <question>, when the owner asks how cards or rules interact, or when an agent meets a rules question.
---

# judge

The skill serves the owner's rules questions and any agent's; nothing runs
it on its own. The Comprehensive Rules are `output/data/rules.txt`, their
headings `output/data/rules-index.md`, each card's Scryfall rulings the
`rulings` key in `output/data/oracle.json`. The scripts run from the folder
that holds `output/`, as `python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/<script>`:

- `fetch-rules.py` downloads the rules linked from Wizards' rules page and
  writes the index; it downloads only when the page links a newer file, so
  it is safe to rerun after a set release.
- `rule.py 800.4a [704.5 ...]` prints rules with their subrules;
  `rule.py --find word ...` the number and opening of every rule holding all
  the words; `rule.py --glossary term` a glossary entry.
- `card.py "Card Name" ...` prints each card's oracle text and rulings, from
  `oracle.json` or, for a card not there, singly from Scryfall.

For `/judge <question>`:

1. If `output/data/rules.txt` is missing, run `fetch-rules.py`.
2. Run `card.py` with every card the question names.
3. Run `rule.py --find` on the question's keywords (keyword abilities,
   zones, game terms such as "leaves the battlefield" or "state-based"),
   then `rule.py <numbers>` for the rules that bear on the question and
   `rule.py --glossary` for its defined terms.
4. Make a fresh scratchpad folder and copy `JUDGE-BRIEF.md` into it with
   `<question>`, `<cards>` (card.py's output), `<rules>` (rule.py's output)
   and `<plugin>` (`${CLAUDE_PLUGIN_ROOT}` expanded) filled in. Dispatch one
   `planner` (`model` from `settings.json`, default
   `claude-opus-5-5`, `run_in_background`) with it, working in the folder
   that holds `output/`.
5. Give its answer in chat: the ruling in a few lines, the CR numbers it
   rests on, a card ruling quoted only when it decides the case. Nothing is
   written to `output/`.
