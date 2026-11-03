"""One-off: split every <output_dir>/decks/<slug>/scores.md into nonlands.md and lands.md, then delete it.
usage: python3 .claude/skills/mtg-score/split-scores.py <output_dir>
Adds and cuts go by <output_dir>/data/oracle.json's type line. A deck whose rows do not all land in
exactly one of the two files is left untouched."""
import sys
from pathlib import Path
from merge import split, cells, tail, lands, by_kind, deck_file, KINDS

if len(sys.argv) != 2: sys.exit(__doc__)
out = Path(sys.argv[1]); land = lands(out / "data/oracle.json")
for p in sorted(out.glob("decks/*/scores.md")):
    s = dict(split(p.read_text()))
    title = s[None][0].removeprefix("# ").removesuffix(": fit scores")
    cards = {"nonlands": cells(s["## Nonlands"]), "lands": cells(s["## Lands"])}
    adds, cuts = (by_kind(cells(s.get(h, [])), land) for h in ("## Adds", "## Cuts"))
    intro = [l for l in s.get("## Adds", []) if l.strip() and not l.startswith("|")]
    rest = {k: tail(intro if k == "nonlands" else [], adds[k], cuts[k]) if "## Adds" in s else [] for k in KINDS}
    texts = {k: deck_file(title, k, cards[k], rest[k]) for k in KINDS}
    before = sorted(map(tuple, cells(l for h in ("## Nonlands", "## Lands", "## Adds", "## Cuts") for l in s.get(h, []))))
    after = sorted(tuple(r) for t in texts.values() for h, ls in split(t) if h in ("## Cards", "## Adds", "## Cuts") for r in cells(ls))
    if before != after: print(f"{p.parent.name}: rows differ, scores.md kept"); continue
    for k, t in texts.items(): (p.parent / f"{k}.md").write_text(t)
    p.unlink()
    print(f"{p.parent.name}: {len(before)} rows; " + ", ".join(
        f"{k} {len(cards[k])} cards, {len(adds[k])} adds, {len(cuts[k])} cuts" for k in KINDS))
