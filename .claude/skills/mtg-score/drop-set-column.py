"""One-off: drop the Set (release) column from the Adds table of every deck's scores.md.
usage: python3 .claude/skills/mtg-score/drop-set-column.py <output_dir>
prints per deck the table rows and score total before and after; a deck that does not match is left as it was."""
import sys
from collections import Counter
from pathlib import Path
from merge import ADDS, split, cells

OLD = "| Card | Score | Note | Set (release) | New | ~Price |"

def scored(text): return Counter((r[0], r[1]) for h, ls in split(text) if h for r in cells(ls))

if len(sys.argv) < 2: sys.exit(__doc__)
bad = 0
for f in sorted(Path(sys.argv[1]).glob("decks/*/scores.md")):
    old = f.read_text().split("\n")
    if OLD not in old: print(f"{f.parent.name}: no Set (release) column"); continue
    i = j = old.index(OLD)
    while j < len(old) and old[j].startswith("|"): j += 1
    rows = [l.split("|") for l in old[i:j]]  # "| a | b |" splits to ["", " a ", " b ", ""]
    new = old[:i] + ["|".join(r[:4] + r[5:]) for r in rows] + old[j:]
    was, now = scored("\n".join(old)), scored("\n".join(new))
    back = new[:i] + ["|".join(n.split("|")[:4] + [r[4]] + n.split("|")[4:]) for n, r in zip(new[i:j], rows)] + new[j:]
    ok = was == now and back == old and new[i] == ADDS and all(len(r) == 8 for r in rows)
    total = lambda n: sum(int(sc) * k for (_, sc), k in n.items() if sc.isdigit())
    print(f"{f.parent.name}: rows {sum(was.values())} -> {sum(now.values())}, score total {total(was)} -> {total(now)},"
          f" adds {j - i - 2}" + ("" if ok else ", MISMATCH: left as it was"))
    if ok: f.write_text("\n".join(new))
    bad += not ok
sys.exit(bad and f"{bad} deck(s) left as they were")
