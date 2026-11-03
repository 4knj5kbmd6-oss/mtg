"""Write a planner's adds and cuts into a deck's nonlands.md and lands.md as their Adds and Cuts tables.
usage (repo root): python3 .claude/skills/mtg-upgrades/apply.py <run_dir> <slug>
reads <run_dir>/<slug>-adds.md and <slug>-cuts.md. Each row goes to lands.md if output/data/oracle.json
says the card is a land, else to nonlands.md. An add already scored keeps its score and note, the rest
get "-" and the research reason; a cut gets its deck score."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / ".claude/skills/mtg-score"))
from merge import split, join, cells, key, tail, lands, by_kind, KINDS

def apply(files, adds, cuts, land):
    """{kind: text} of a deck's nonlands.md and lands.md with their Adds and Cuts sections rebuilt from the
    research files' texts, each row in the file land(card) picks"""
    secs = {k: split(t) for k, t in files.items()}; old = [dict(s) for s in secs.values()]
    done = {key(r[0]): r[1:3] for o in old for r in cells(o.get("## Adds", [])) if r[1] != "-"}
    deck = {key(r[0]): r[1] for o in old for r in cells(o.get("## Cards", []))}
    new = by_kind([[n, *done.get(key(n), ["-", why]), "Yes" if since.startswith("Yes") else "No", price]
                   for _, n, since, why, price in cells(adds.splitlines())], land)
    cut = by_kind([[n, deck.get(key(n), "-"), why] for _, n, why in cells(cuts.splitlines())], land)
    intro = [l for l in adds.splitlines()[1:] if l.strip() and not l.startswith("|")]
    out = {}
    for k, s in secs.items():
        s = [x for x in s if x[0] not in ("## Adds", "## Cuts")]
        at = next((i for i, x in enumerate(s) if x[0] == "## Shape"), len(s))
        out[k] = join(s[:at] + tail(intro if k == "nonlands" else [], new[k], cut[k]) + s[at:])
    return out

if __name__ == "__main__":
    if len(sys.argv) < 3: sys.exit(__doc__)
    run, slug = sys.argv[1], sys.argv[2]
    deck = ROOT / f"output/decks/{slug}"
    paths = {k: deck / f"{k}.md" for k in KINDS}
    research = (Path(f"{run}/{slug}-{x}.md").read_text() for x in ("adds", "cuts"))
    for k, text in apply({k: p.read_text() for k, p in paths.items()}, *research, lands(ROOT / "output/data/oracle.json")).items():
        paths[k].write_text(text)
    print(f"{slug}: Adds and Cuts written to {deck.relative_to(ROOT)}/nonlands.md and lands.md")
