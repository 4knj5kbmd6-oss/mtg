"""A deck's mana facts from its list and oracle.json, its <run_dir>/<slug>-mana.md, for facts.py and the mana skill.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/mana/mana.py <run_dir> <slug> [slug ...]
write() counts card copies of output/decks/<slug>/list.txt, commanders included: the lands; the nonlands, their mean
mana value and curve; the chance of at least 2 lands by turn 2, 3 by turn 3 and 4 by turn 4 (odds.py) drawn from the
deck without its commanders; and per colour of the commanders' identity, the land sources, the sources needed and the
card that sets them, the nonland sources, the pips, the cards with two or more pips of it and the lowest mana value
among those. A nonland card with pips of a colour needs the fewest of the deck's lands to be sources of it that give it
at least that many among the cards seen by the turn of its mana value, 7 at most, 90% of the times at least its mana
value of lands are seen, or its pips when more; - when the deck has too few lands to see that many. The colour needs
the most any of its cards needs (ties: the lowest mana value, then by name). A chance or need is unknown when fewer of
the deck's cards are known than are seen by its turn. A card's colours are its produced_mana within the identity; a fetch land's are also those of
the basic land types it searches for, or every colour of the identity when it searches for a basic land card of no
type. Pips are the {W} {U} {B} {R} {G} symbols of the front face's cost. Prints any card oracle.json lacks, left out of
the counts."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import ORACLE, decklist, front, is_land
from tables import table
import odds

COLOURS = "WUBRG"
TYPES = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}
FETCH = re.compile(r"search your library for ([^.]*)", re.I)
CURVE = [str(n) for n in range(7)] + ["7+"]
CHANCE = 0.9

def colours(e, identity):
    """the colours of the identity e makes mana of, a fetch land's by the land types it searches for"""
    got = set(e.get("produced_mana") or [])
    if is_land(e):
        for want in FETCH.findall(front(e).get("oracle_text", "")):
            typed = {c for t, c in TYPES.items() if re.search(rf"\b{t}\b", want)}
            got |= typed or (set(identity) if "basic land card" in want else set())
    return got & set(identity)

def pips(e, colour): return front(e).get("mana_cost", "").count(f"{{{colour}}}")

def turn(e): return min(int(e.get("cmc", 0)), 7)

def needed(e, colour, lands, size):
    """the fewest of the lands in a deck of size cards to be sources of the colour that give e its pips of it by its turn
    CHANCE of the times its lands are seen, None when none do"""
    want, seen = pips(e, colour), odds.seen(turn(e))
    least = max(int(e.get("cmc", 0)), want)
    return next((s for s in range(want, lands + 1)
                 if odds.given_lands(want, s, lands, size, seen, least) >= CHANCE), None)

def page(slug, commanders, rest):
    """the mana file's text from [(copies, oracle entry)] of the commanders and of the rest of the deck"""
    deck = commanders + rest
    identity = [c for c in COLOURS if any(c in e.get("color_identity", []) for _, e in commanders)]
    lands = [(n, e) for n, e in deck if is_land(e)]
    spells = [(n, e) for n, e in deck if not is_land(e)]
    count = lambda cards: sum(n for n, _ in cards)
    mean = sum(n * e.get("cmc", 0) for n, e in spells) / max(count(spells), 1)
    curve = [count((n, e) for n, e in spells if turn(e) == i) for i in range(8)]
    size, landed = count(rest), count((n, e) for n, e in rest if is_land(e))
    known = lambda t: size >= odds.seen(t)
    on_curve = [f"{odds.at_least(k, landed, size, odds.seen(k)):.0%}" if known(k) else "unknown" for k in (2, 3, 4)]
    rows = []
    for c in identity:
        sources = lambda cards: count((n, e) for n, e in cards if c in colours(e, identity))
        heavy = [(n, e) for n, e in spells if pips(e, c) >= 2]
        lowest = f"{min(e.get('cmc', 0) for _, e in heavy):g}" if heavy else "-"
        wanting = [e for _, e in spells if pips(e, c)]
        told = wanting and all(known(turn(e)) for e in wanting)
        needs = {e["name"]: needed(e, c, landed, size) for e in wanting} if told else {}
        most = lambda e: needs[e["name"]] or landed + 1
        top = min(wanting, key=lambda e: (-most(e), e.get("cmc", 0), e["name"])) if told else None
        need = [str(needs[top["name"]] or "-"), top["name"]] if top else ["unknown" if wanting else "-", "-"]
        rows.append([c, str(sources(lands)), *need,
                     *map(str, (sources(spells), sum(n * pips(e, c) for n, e in spells), count(heavy))), lowest])
    return "\n".join([f"# {slug}: mana", "",
                      "## Curve", table("| Lands | Nonlands | Mean mana value | " + " | ".join(CURVE) + " |",
                                        [[str(count(lands)), str(count(spells)), f"{mean:.1f}", *map(str, curve)]]), "",
                      "## Lands", table("| 2 by turn 2 | 3 by turn 3 | 4 by turn 4 |", [on_curve]), "",
                      "## Colours", table("| Colour | Land sources | Sources needed | For | Nonland sources | Pips |"
                                          " Cards with 2+ pips | Lowest mana value of those |", rows), ""])

def write(run, slug):
    cards = json.loads(ORACLE.read_text())["cards"]
    named = {f.casefold(): e for n, e in cards.items() for f in n.split(" // ")} | {n.casefold(): e for n, e in cards.items()}
    commanders, rest = decklist(slug)
    if missing := [n for _, n in commanders + rest if n.casefold() not in named]:
        print(f"{slug}: not in oracle.json:", ", ".join(missing))
    entries = lambda part: [(c, named[n.casefold()]) for c, n in part if n.casefold() in named]
    Path(run, f"{slug}-mana.md").write_text(page(slug, entries(commanders), entries(rest)))

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    for slug in sys.argv[2:]: write(sys.argv[1], slug)

if __name__ == "__main__": main()
