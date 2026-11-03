"""Write the researcher's adds and cuts into a deck's nonlands.md and lands.md as their Adds and Cuts tables.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/apply.py <run_dir> <slug>
reads <run_dir>/<slug>-adds.md and <slug>-cuts.md. Each row goes to lands.md if output/data/oracle.json
says the card is a land, else to nonlands.md. An add already scored keeps its score and note, the rest
get "-" and the research reason; a cut gets its deck score. An add named on restricted.md or the deck's
own restricted.md (either face of a double-faced card) is dropped, and so is an add whose ~Price is above
the budget in settings.json (a price that does not parse is kept); the drops are printed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "score"))
from merge import split, join, cells, key, tail, lands, by_kind, KINDS, DECKS
from settings import settings

def restricted(paths):
    """the card names (each face apart) on the bullet lines of those restricted.md files that exist"""
    return {f.strip() for p in paths if p.exists() for l in p.read_text().splitlines()
            if l.startswith(("- ", "* ")) for f in l[2:].split(" // ")}

def drop(adds, hit):
    """(an adds file's text without the rows hit(row's cells) is true of, the dropped cards)"""
    gone = lambda line: [r[1] for r in cells([line]) if len(r) > 1 and hit(r)]
    dropped = [n for l in adds.splitlines() for n in gone(l)]
    return "\n".join(l for l in adds.splitlines() if not gone(l)), dropped

def price(cell):
    """the dollars in a ~Price cell such as "$12.38", or None when it does not parse"""
    try: return float(cell.strip().lstrip("~$").replace(",", ""))
    except ValueError: return None

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
    deck = DECKS / slug
    paths = {k: deck / f"{k}.md" for k in KINDS}
    names = restricted([Path("restricted.md"), deck / "restricted.md"])
    adds, dropped = drop(Path(f"{run}/{slug}-adds.md").read_text(), lambda r: set(map(str.strip, r[1].split(" // "))) & names)
    if dropped: print(f"{slug}: restricted, not added: {', '.join(dropped)}")
    if (budget := settings()["budget"]) is not None:
        adds, dropped = drop(adds, lambda r: (p := price(r[-1])) is not None and p > budget)
        if dropped: print(f"{slug}: above the ${budget:g} budget, not added: {', '.join(dropped)}")
    cuts = Path(f"{run}/{slug}-cuts.md").read_text()
    for k, text in apply({k: p.read_text() for k, p in paths.items()}, adds, cuts, lands()).items():
        paths[k].write_text(text)
    print(f"{slug}: Adds and Cuts written to {deck}/nonlands.md and lands.md")
