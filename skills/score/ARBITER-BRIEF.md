# Arbiter brief

Paths are relative to your working directory, the folder that holds output/.

Read <scoring> (anchors and rules). Read <run>/<slug>-flagged.md: cards
where the independent scorers differed by 3 or more, with their scores and
notes. For each card read the owner's output/decks/<slug>/plan.md (authoritative on
the deck's lines), the card's text in output/data/oracle.json and the list
output/decks/<slug>/list.txt. Where scorers disagree on a rules question, settle the
rule first (cite the Comprehensive Rules or an official ruling if it is not
plain from the text). Rule a final 0 to 10.

Write <run>/arb-<slug>.json: {"<exact card name>": {"score": n, "note":
"<at most 12 words: role and reason, no mention of scorers>"}, ...}.
Final message: one line per card, "card: A,B,C -> ruling, reason".
