"""Write each deck's three fact files into <run_dir>: <slug>-combos.md, its combos from Commander Spellbook
(combos.py); <slug>-mana.md, its mana from its list and oracle.json (skills/mana/mana.py), ending with its Mana level,
the ranker's Mana table applied to mana.py's numbers, or `-` when the deck's plan.md excludes Mana; and
<slug>-counts.md, per category the list's cards that oracle.json's tags put in it, by CATEGORIES below.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/facts.py <run_dir> <slug> [slug ...]
Prints the cards of each deck Spellbook or oracle.json does not know. When Spellbook is unreachable it prints one
line naming the URL, and the deck gets no combos file."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mana"))
from project import DECKS, ORACLE, decklist, front
from tables import table
import combos, mana

# The tag-to-category map. A card's oracle.json tags are Scryfall's functional tags, each with every tag above it in
# the tag tree, so a parent tag stands for all its children. A card is in a category when its tags hold one of the
# category's tags and none of its excluded ones: a land tutor is ramp, not a tutor, and a sweeper is a wipe, not
# removal. Answers are the counters, removal and wipes with the redirects and stax or hate pieces of ANSWERS; an
# instant-speed answer is an instant or has flash.
CATEGORIES = {"Tutors": ({"tutor"}, {"tutor-land"}),
              "Draw engines": ({"draw engine", "repeatable impulsive draw"}, set()),
              "Recursion": ({"recursion"}, set()),
              "Protection": ({"protection"}, set()),
              "Counters": ({"counterspell"}, set()),
              "Removal": ({"removal"}, {"sweeper"}),
              "Wipes": ({"sweeper"}, set())}
ANSWERS = {"change target", "hatebear", "silence", "prevent cast", "prevent activation", "hate-graveyard", "hate-tutor"}
ROWS = ["Tutors", "Draw engines", "Recursion", "Protection", "Answers", "Instant-speed answers", "Counters", "Removal",
        "Wipes"]
FLASH = re.compile(r"^(?:\w[\w ]*, )*flash(?:,|$)", re.I | re.M)
EXCLUDED = re.compile(r"^- \*\*Mana:\*\*\s*excluded\s*$", re.M)

def counts(run, slug):
    """write <run>/<slug>-counts.md: per category of ROWS the list's card copies in it and their names, commanders in
    and the SIDEBOARD block out; a card oracle.json lacks is in none"""
    cards = json.loads(ORACLE.read_text())["cards"]
    named = {f.casefold(): e for n, e in cards.items() for f in n.split(" // ")} | {n.casefold(): e for n, e in cards.items()}
    commanders, rest = decklist(slug)
    found = {r: {} for r in ROWS}
    for copies, name in commanders + rest:
        if (e := named.get(name.casefold())) is None: continue
        tags = set(e.get("tags", []))
        into = [c for c, (want, not_) in CATEGORIES.items() if tags & want and not tags & not_]
        if {"Counters", "Removal", "Wipes"} & set(into) or tags & ANSWERS:
            into.append("Answers")
            face = front(e)
            if "Instant" in face.get("type_line", "").split() or FLASH.search(face.get("oracle_text", "")):
                into.append("Instant-speed answers")
        for c in into: found[c][name] = found[c].get(name, 0) + copies
    rows = [[r, str(sum(found[r].values())), "; ".join(sorted(found[r])) or "-"] for r in ROWS]
    Path(run, f"{slug}-counts.md").write_text(f"# {slug}: counts\n\n" + table("| Category | Count | Cards |", rows) + "\n")

def level(castable, ramp, short):
    """the Mana criterion's level, 1 to 9, by the ranker's Mana table, from mana.py's numbers: Castable and Ramp as
    whole percents and Short; a number None, the deck too small to know it, meets no bar"""
    castable, ramp = (None if x is None else round(x * 100) for x in (castable, ramp))
    if castable is None or castable < 75: return 1
    fast = lambda least: ramp is not None and ramp >= least
    fine = lambda most: short is not None and short <= most
    if castable >= 90 and fast(35) and fine(0): return 9
    if castable >= 87 and fast(25) and fine(2): return 7
    return 5 if castable >= 84 and fine(4) else 3

def excluded(slug):
    """whether the deck's plan.md excludes Mana by a `- **Mana:** excluded` bullet"""
    path = DECKS / slug / "plan.md"
    return path.exists() and bool(EXCLUDED.search(path.read_text()))

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    run = sys.argv[1]
    for slug in sys.argv[2:]:
        combos.write(run, slug)
        numbers = mana.write(run, slug)
        path = Path(run, f"{slug}-mana.md")
        path.write_text(path.read_text() + f"\nMana level: {'-' if excluded(slug) else level(**numbers)}\n")
        counts(run, slug)

if __name__ == "__main__": main()
