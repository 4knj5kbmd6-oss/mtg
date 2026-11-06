"""Write each deck's two fact files into <run_dir>: <slug>-combos.md, its combos from Commander Spellbook (combos.py),
and <slug>-counts.md, per category the list's cards that oracle.json's tags put in it, by CATEGORIES below.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/facts.py <run_dir> <slug> [slug ...]
Prints the cards of each deck Spellbook does not know. When Spellbook is unreachable it prints one line naming the URL,
and the deck gets no combos file."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import ORACLE, decklist, front
from tables import table
import combos

# The tag-to-category map. A card's oracle.json tags are Scryfall's functional tags, each with every tag above it in
# the tag tree, so a parent tag stands for all its children. A card is in a category when its tags hold one of the
# category's tags and none of its excluded ones: a sweeper is a wipe, not removal. Answers are the counters, removal
# and wipes with the redirects and stax or hate pieces of ANSWERS; an instant-speed answer is an instant or has flash.
CATEGORIES = {"Recursion": ({"recursion"}, set()),
              "Protection": ({"protection"}, set()),
              "Counters": ({"counterspell"}, set()),
              "Removal": ({"removal"}, {"sweeper"}),
              "Wipes": ({"sweeper"}, set())}
ANSWERS = {"change target", "hatebear", "silence", "prevent cast", "prevent activation", "hate-graveyard", "hate-tutor"}
ROWS = ["Recursion", "Protection", "Answers", "Instant-speed answers", "Counters", "Removal", "Wipes"]
FLASH = re.compile(r"^(?:\w[\w ]*, )*flash(?:,|$)", re.I | re.M)

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

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    run = sys.argv[1]
    for slug in sys.argv[2:]:
        combos.write(run, slug)
        counts(run, slug)

if __name__ == "__main__": main()
