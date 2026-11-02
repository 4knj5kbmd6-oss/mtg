"""One-off: fold each deck's adds.md and cuts.md into its scores.md as the Adds and Cuts tables,
keeping the scores in its Recommended adds, then delete the two files.
usage: python3 .claude/skills/mtg-score/migrate-adds-cuts.py <output_dir>
prints per deck the cards and score total before and after; a deck that does not match is left as it was."""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mtg-upgrades"))
from apply import apply
from merge import split, cells

def table(text, *heads):
    secs = dict(split(text)); return [r for h in heads for r in cells(secs.get(h, []))]

def rest(text): return [s for s in split(text) if s[0] not in ("## Recommended adds", "## Adds", "## Cuts")]

if len(sys.argv) < 2: sys.exit(__doc__)
bad = 0
for d in sorted(p.parent for p in Path(sys.argv[1]).glob("decks/*/adds.md")):
    s, a, c = ((d / f).read_text() for f in ("scores.md", "adds.md", "cuts.md"))
    new = apply(s.replace("\n## Recommended adds\n", "\n## Adds\n"), a, c)
    was = Counter((r[0], r[1]) for r in table(s, "## Nonlands", "## Lands", "## Recommended adds"))
    now = Counter((r[0], r[1]) for r in table(new, "## Nonlands", "## Lands", "## Adds"))
    adds = (sorted((r[1], r[2], r[5]) for r in cells(a.splitlines())), sorted((r[0], r[3], r[5]) for r in table(new, "## Adds")))
    cuts = (sorted((r[1], r[2]) for r in cells(c.splitlines())), sorted((r[0], r[2]) for r in table(new, "## Cuts")))
    ok = (was == now and adds[0] == adds[1] and cuts[0] == cuts[1] and rest(s) == rest(new)
          and all(r[1].isdigit() for r in table(new, "## Adds", "## Cuts")))
    total = lambda n: sum(int(sc) * k for (_, sc), k in n.items())
    print(f"{d.name}: cards {sum(was.values())} -> {sum(now.values())}, score total {total(was)} -> {total(now)},"
          f" adds {len(adds[0])} -> {len(adds[1])}, cuts {len(cuts[0])} -> {len(cuts[1])}" + ("" if ok else ", MISMATCH: left as it was"))
    if ok:
        (d / "scores.md").write_text(new); (d / "adds.md").unlink(); (d / "cuts.md").unlink()
    bad += not ok
sys.exit(bad and f"{bad} deck(s) left as they were")
