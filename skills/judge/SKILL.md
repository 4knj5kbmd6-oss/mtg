---
name: judge
description: Answer a Magic rules question with a judge agent given the named cards' oracle text and Scryfall rulings and the matching Comprehensive Rules, citing the rule numbers; fetch the Comprehensive Rules into output/data/rules.txt. Use for /judge <question>, when the owner asks how cards or rules interact, or when an agent meets a rules question.
argument-hint: "<question>"
---

# judge

The Comprehensive Rules are `output/data/rules.txt`, each card's Scryfall
rulings the `rulings` key in `output/data/oracle.json`. The scripts run from
the folder that holds `output/`, as
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/<script>`.

Settings and dispatch as the deck-files skill's Dispatch section says.

For `/judge <question>`:

1. If `output/data/rules.txt` is missing, run `fetch_rules.py`.
2. Run `card.py` with every card the question names.
3. Run `rule.py --find` on the question's keywords (keyword abilities,
   zones, game terms such as "leaves the battlefield" or "state-based"),
   then `rule.py <numbers>` for the rules that bear on the question and
   `rule.py --glossary` for its defined terms.
4. Dispatch one `mtg-toolbox:judge`, its prompt giving the question,
   card.py's output and rule.py's output.
5. Give its answer in chat. Nothing is written to `output/`.
