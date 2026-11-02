"""Write a planner's adds and cuts into a deck's scores.md as its Adds and Cuts tables.
usage (repo root): python3 .claude/skills/mtg-upgrades/apply.py <run_dir> <slug>
reads <run_dir>/<slug>-adds.md and <slug>-cuts.md. An add already scored keeps its score and note,
the rest get "-" and the research reason; a cut gets its deck score."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".claude/skills/mtg-score"))
from merge import split, join, cells, key, tail

def apply(scores, adds, cuts):
    """scores.md text with its Adds and Cuts sections rebuilt from the research files' texts"""
    secs = split(scores); old = dict(secs)
    done = {key(r[0]): r[1:3] for r in cells(old.get("## Adds", [])) if r[1] != "-"}
    deck = {key(r[0]): r[1] for h in ("## Nonlands", "## Lands") for r in cells(old.get(h, []))}
    new = [[n, *done.get(key(n), ["-", why]), src, "Yes" if since.startswith("Yes") else "No", price]
           for _, n, src, since, why, price in cells(adds.splitlines())]
    cut = [[n, deck.get(key(n), "-"), why] for _, n, why in cells(cuts.splitlines())]
    intro = [l for l in adds.splitlines()[1:] if l.strip() and not l.startswith("|")]
    secs = [s for s in secs if s[0] not in ("## Adds", "## Cuts")]
    at = next((i for i, s in enumerate(secs) if s[0] == "## Shape"), len(secs))
    return join(secs[:at] + tail(intro, new, cut) + secs[at:])

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    run, slug = sys.argv[1], sys.argv[2]
    path = ROOT / f"output/decks/{slug}/scores.md"
    path.write_text(apply(path.read_text(), *(Path(f"{run}/{slug}-{x}.md").read_text() for x in ("adds", "cuts"))))
    print(f"{slug}: Adds and Cuts written to {path.relative_to(ROOT)}")
