---
name: score-deck
description: Rank every one of your Commander decks by strength (independent rankers, merged), and write rankings.md beside output/. Use when asked to rank the decks, after /score-cards, or after a change to a ranking criterion.
argument-hint: "[key=value ...]"
---

# score-deck

Ranks every deck under `output/decks/` that has a `list.txt`.

Settings and dispatch as the deck-files skill's Dispatch section says.

1. Make a fresh scratchpad folder `<run>/` and write every deck's two fact
   files,
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score-deck/facts.py <run> <slug> ...`
   given every slug under `output/decks/` that has a `list.txt`.
2. Dispatch `rankers` `mtg-toolbox:ranker` agents, lettered A, B, C and on,
   each prompt giving `<run>` as an absolute path, the letter and those
   slugs, in the same order for every ranker, and nothing else; they read
   each deck's two fact files in `<run>`: combos and counts.
3. When all are back, run
   `python3 ${CLAUDE_PLUGIN_ROOT}/skills/score-deck/merge_rankings.py <run>`;
   when it exits naming a ranker file, re-dispatch that letter alone and
   merge again.
4. Copy `<run>/rankings.md` over `rankings.md`.

After a change to a computed criterion alone (merge_rankings.py's
`COMPUTED`), run `facts.py <run>` with every slug as in step 1, then
`python3 ${CLAUDE_PLUGIN_ROOT}/skills/score-deck/merge_rankings.py --recompute <run>`,
then copy `<run>/rankings.md` over `rankings.md`; no ranker runs. A change
to a judged criterion or its levels still ranks the decks.

Report: per deck its score from `rankings.md`, its Interaction and Card
quality named as computed.
