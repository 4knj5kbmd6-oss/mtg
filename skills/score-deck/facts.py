"""Write each deck's two fact files into <run_dir>: <slug>-combos.md, its combos from Commander Spellbook (combos.py),
and <slug>-counts.md, per category the list's cards that oracle.json's tags put in it, by CATEGORIES below, then its
Game Changers, by game_changers() below, ending with the deck's four Card quality levels, by quality() below.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score-deck/facts.py <run_dir> <slug> [slug ...]
Writes each deck's counts file before its combos file. Prints, per deck, the list's cards oracle.json lacks, commanders
included, and the cards Spellbook does not know. When Spellbook is unreachable it prints one line naming the URL, and the
deck gets no combos file."""
import math, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mana"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "score-cards"))
from project import decklist, front, named
from tables import table
from mana import land_drop
import combos

# The tag-to-category map. A card's oracle.json tags are Scryfall's functional tags, each with every tag above it in
# the tag tree, so a parent tag stands for all its children. A card is in a category when its tags hold one of the
# category's tags and none of its excluded ones: a sweeper is a wipe, not removal. Creature and noncreature removal
# are the cards tagged removal, sweepers in, since a wipe answers the kinds it hits, by their target tags:
# removal-creature, or removal-artifact, -enchantment, -planeswalker or -land, a narrower target (removal-aura,
# -equipment, -vehicle) carrying its parent's tag; a removal card with neither is split by its front face's text
# instead, by TEXT: it names creatures, or artifacts, enchantments, planeswalkers or lands, a permanent being both.
# Answers are the counters, removal and wipes with the redirects and stax or hate pieces of ANSWERS; an instant-speed
# answer is an instant or has flash.
CATEGORIES = {"Recursion": ({"recursion"}, set()),
              "Protection": ({"protection"}, set()),
              "Counters": ({"counterspell"}, set()),
              "Removal": ({"removal"}, {"sweeper"}),
              "Creature removal": ({"removal-creature"}, set()),
              "Noncreature removal": ({"removal-artifact", "removal-enchantment", "removal-planeswalker", "removal-land"},
                                      set()),
              "Wipes": ({"sweeper"}, set())}
TEXT = {"Creature removal": re.compile(r"\b(creature|permanent)s?\b", re.I),
        "Noncreature removal": re.compile(r"\b(artifact|enchantment|planeswalker|land|permanent)s?\b", re.I)}
ANSWERS = {"change target", "hatebear", "silence", "prevent cast", "prevent activation", "hate-graveyard", "hate-tutor"}
ROWS = ["Recursion", "Protection", "Answers", "Instant-speed answers", "Counters", "Removal", "Creature removal",
        "Noncreature removal", "Wipes"]
FLASH = re.compile(r"^(?:\w[\w ]*, )*flash(?:,|$)", re.I | re.M)
# Card quality is four levels, each 1 to 9, from each card's EDHREC saltiness (salt) and USD price (price) in
# oracle.json, the commanders apart from the 99. 99 salt is the mean over the 99's copies, a land under PLAIN left out
# (basics, plain duals), 0.30 level 1 and 0.90 level 9; Commander salt is the commanders' salts summed, on the same
# levels. 99 price is the 99's prices summed per copy, 125 dollars level 1 and 4,000 level 9 on a log scale; Commander
# price the commanders' prices summed, 1 dollar level 1 and 100 level 9. A card with no value adds nothing. A card of
# the 99 at SALTY or more, or at PRICEY dollars or more, is named.
PLAIN, SALTY, PRICEY = 0.5, 2.0, 20.0

def held(x):
    """x rounded half up and held to 1 to 9"""
    return min(9, max(1, math.floor(x + 0.5)))

def salt_level(s):
    """1 + 8 * (s - 0.3) / 0.6, held"""
    return held(1 + 8 * (s - 0.3) / 0.6)

def price_level(usd, low, high):
    """1 + 8 * ln(usd / low) / ln(high / low), held; 1 with no usd"""
    return held(1 + 8 * math.log(usd / low) / math.log(high / low)) if usd > 0 else 1

def quality(slug):
    """the counts file's four Card quality rows, [Category, level, Cards], the commanders apart from the 99 (the rest of
    the list, the SIDEBOARD block out), each over the copies with a value, a land drop under PLAIN salt left out:
    Commander salt and Commander price the commanders' values summed, their Cards the sum and each commander with its
    value; 99 salt the 99's mean, its Cards the mean, the copies it is over and the cards at SALTY or more; 99 price the
    99's sum, its Cards the sum, the copies it is over and the cards at PRICEY or more; cards highest first"""
    oracle = named()
    commanders, rest = decklist(slug)
    def valued(cards, field):
        """[(copies, name, value)] of the cards with a value of field"""
        return [(c, n, e[field]) for c, n in cards if (e := oracle.get(n.casefold())) and e.get(field) is not None
                and not (field == "salt" and land_drop(e) and e["salt"] < PLAIN)]
    def named_at(found, at, shown):
        """the cards of found at at or more, highest first, each with its value shown, joined by "; ", or -"""
        return "; ".join(f"{n} {shown(v)}" for n, v in sorted({(n, v) for _, n, v in found if v >= at},
                                                              key=lambda c: (-c[1], c[0]))) or "-"
    total, n = (lambda found: sum(c * v for c, _, v in found)), (lambda found: sum(c for c, _, _ in found))
    salt, usd = (lambda v: f"{v:.2f}"), (lambda v: f"${v:.2f}")
    lead_salt, lead_price, salts, prices = (valued(cards, field) for cards, field in
                                            ((commanders, "salt"), (commanders, "price"), (rest, "salt"), (rest, "price")))
    mean = total(salts) / n(salts) if salts else 0
    return [["Commander salt", str(salt_level(total(lead_salt))),
             f"sum {salt(total(lead_salt))}; {named_at(lead_salt, 0, salt)}"],
            ["Commander price", str(price_level(total(lead_price), 1, 100)),
             f"sum {usd(total(lead_price))}; {named_at(lead_price, 0, usd)}"],
            ["99 salt", str(salt_level(mean)), f"mean {salt(mean)} over {n(salts)} cards; {named_at(salts, SALTY, salt)}"],
            ["99 price", str(price_level(total(prices), 125, 4000)),
             f"sum {usd(total(prices))} over {n(prices)} cards; {named_at(prices, PRICEY, usd)}"]]

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
    its four Card quality rows, by quality()"""
    oracle = named()
    commanders, rest = decklist(slug)
    found = {r: {} for r in ROWS}
    for copies, name in commanders + rest:
        if (e := oracle.get(name.casefold())) is None: continue
        tags = set(e.get("tags", []))
        into, face = [c for c, (want, not_) in CATEGORIES.items() if tags & want and not tags & not_], front(e)
        if "removal" in tags and not TEXT.keys() & set(into):
            into += [c for c, text in TEXT.items() if text.search(face.get("oracle_text", ""))]
        if {"Counters", "Removal", "Wipes"} & set(into) or tags & ANSWERS:
            into.append("Answers")
            if "Instant" in face.get("type_line", "").split() or FLASH.search(face.get("oracle_text", "")):
                into.append("Instant-speed answers")
        for c in into: found[c][name] = found[c].get(name, 0) + copies
    rows = [[r, str(sum(found[r].values())), "; ".join(sorted(found[r])) or "-"] for r in ROWS]
    changers = game_changers(slug)
    rows.append(["Game Changers", str(len(changers)), "; ".join(changers) or "-"])
    rows += quality(slug)
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
