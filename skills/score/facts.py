"""Write each deck's two fact files into <run_dir>: <slug>-combos.md, its combos from Commander Spellbook (combos.py),
and <slug>-counts.md, per category the list's cards that oracle.json's tags put in it, by CATEGORIES below, then its
Game Changers, by game_changers() below, ending with the deck's Salt level, by salt() below.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/facts.py <run_dir> <slug> [slug ...]
Writes each deck's counts file before its combos file. Prints, per deck, the list's cards oracle.json lacks, commanders
included, and the cards Spellbook does not know. When Spellbook is unreachable it prints one line naming the URL, and the
deck gets no combos file."""
import math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mana"))
from project import decklist, front, named
from tables import table
from mana import land_drop
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
# Salt is each card's EDHREC saltiness in oracle.json. A land under PLAIN is left out of the deck's mean (basics, plain
# duals); a mean of 0.30 is level 1, each 0.075 above it one level more, 0.90 level 9. A card at SALTY or more is named.
PLAIN, SALTY = 0.5, 2.0

def salt(slug):
    """(mean, cards, level, salty) of the deck: its mean salt over the list's copies, commanders in and the SIDEBOARD
    block out, leaving out a card with no salt value or none in oracle.json and a land drop under PLAIN; the copies the
    mean is over; the level, 1 + 8 * (mean - 0.3) / 0.6 rounded and held to 1 to 9; [(name, salt)] of the cards at
    SALTY or more, saltiest first"""
    oracle = named()
    commanders, rest = decklist(slug)
    found = [(copies, name, e["salt"]) for copies, name in commanders + rest
             if (e := oracle.get(name.casefold())) and e.get("salt") is not None and not (land_drop(e) and e["salt"] < PLAIN)]
    n = sum(c for c, _, _ in found)
    mean = sum(c * s for c, _, s in found) / n if n else 0
    level = min(9, max(1, math.floor(1 + 8 * (mean - 0.3) / 0.6 + 0.5)))
    return mean, n, level, sorted({(name, s) for _, name, s in found if s >= SALTY}, key=lambda c: (-c[1], c[0]))

def game_changers(slug):
    """the sorted front-face names of the list's cards, commanders in and the SIDEBOARD block out, whose oracle.json
    entry has game_changer"""
    oracle = named()
    commanders, rest = decklist(slug)
    return sorted({name.split(" // ")[0] for _, name in commanders + rest
                   if (oracle.get(name.casefold()) or {}).get("game_changer")})

def counts(run, slug):
    """write <run>/<slug>-counts.md: per category of ROWS the list's card copies in it and their names, commanders in
    and the SIDEBOARD block out, a card oracle.json lacks in none; then its Game Changers row, by game_changers(), and
    its Salt row, by salt()"""
    oracle = named()
    commanders, rest = decklist(slug)
    found = {r: {} for r in ROWS}
    for copies, name in commanders + rest:
        if (e := oracle.get(name.casefold())) is None: continue
        tags = set(e.get("tags", []))
        into = [c for c, (want, not_) in CATEGORIES.items() if tags & want and not tags & not_]
        if {"Counters", "Removal", "Wipes"} & set(into) or tags & ANSWERS:
            into.append("Answers")
            face = front(e)
            if "Instant" in face.get("type_line", "").split() or FLASH.search(face.get("oracle_text", "")):
                into.append("Instant-speed answers")
        for c in into: found[c][name] = found[c].get(name, 0) + copies
    rows = [[r, str(sum(found[r].values())), "; ".join(sorted(found[r])) or "-"] for r in ROWS]
    changers = game_changers(slug)
    rows.append(["Game Changers", str(len(changers)), "; ".join(changers) or "-"])
    mean, n, level, salty = salt(slug)
    rows.append(["Salt", str(level),
                 f"mean {mean:.2f} over {n} cards; " + ("; ".join(f"{c} {s:.1f}" for c, s in salty) or "-")])
    Path(run, f"{slug}-counts.md").write_text(f"# {slug}: counts\n\n" + table("| Category | Count | Cards |", rows) + "\n")

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    run = sys.argv[1]
    oracle = named()
    for slug in sys.argv[2:]:
        counts(run, slug)
        commanders, rest = decklist(slug)
        if lacking := [n for _, n in commanders + rest if n.casefold() not in oracle]:
            print(f"{slug}: not in oracle.json:", ", ".join(lacking))
        combos.write(run, slug)

if __name__ == "__main__": main()
