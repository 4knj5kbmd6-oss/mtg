---
name: judge
description: Answer a Magic rules question with a judge agent given the named cards' oracle text and Scryfall rulings and the matching Comprehensive Rules, citing the rule numbers; fetch the Comprehensive Rules into output/data/rules.txt. Use for /judge <question>, when the owner asks how cards or rules interact, or when an agent meets a rules question.
argument-hint: "<question>"
---

# judge

The Comprehensive Rules are `output/data/rules.txt`, each card's Scryfall
rulings the `rulings` key in `output/data/oracle.json`. The scripts run from
the folder that holds `output/`, as
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/<script>`:

- `fetch-rules.py` downloads the rules linked from Wizards' rules page; it
  downloads only when the page links a newer file.
- `rule.py 800.4a [704.5 ...]` prints rules with their subrules;
  `rule.py --find word ...` the number and opening of every rule holding all
  the words; `rule.py --glossary term` a glossary entry.
- `card.py "Card Name" ...` prints each card's oracle text and rulings, from
  `oracle.json` or, for a card not there, singly from Scryfall.

Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/settings.py` with the
arguments' `key=value` words for this run's settings. Dispatch every agent
`run_in_background` in the folder that holds `output/`, with `model` only
when it differs from the agent's own; its prompt carries only the per-run
inputs named below.

For `/judge <question>`:

1. If `output/data/rules.txt` is missing, run `fetch-rules.py`.
2. Run `card.py` with every card the question names.
3. Run `rule.py --find` on the question's keywords (keyword abilities,
   zones, game terms such as "leaves the battlefield" or "state-based"),
   then `rule.py <numbers>` for the rules that bear on the question and
   `rule.py --glossary` for its defined terms.
4. Dispatch one `mtg-toolbox:judge`, its prompt giving the question,
   card.py's output and rule.py's output.
5. Give its answer in chat. Nothing is written to `output/`.
