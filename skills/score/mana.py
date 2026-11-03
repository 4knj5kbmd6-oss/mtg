"""A deck's mana facts from its list and oracle.json, its <run_dir>/<slug>-mana.md, for facts.py.
write() counts card copies of output/decks/<slug>/list.txt, commanders included: the lands; the nonlands, their mean mana
value and curve; the odds of exactly 2, 3 and 4 lands in an opening seven drawn from the deck without its
commanders, unknown when fewer than seven of its cards are known; and per colour of the commanders' identity, the land sources, the nonland sources, the pips, the cards
with two or more pips of it and the lowest mana value among those. A card's colours are its produced_mana within the
identity; a fetch land's are also those of the basic land types it searches for, or every colour of the identity
when it searches for a basic land card of no type. Pips are the {W} {U} {B} {R} {G} symbols of the front face's
cost. Prints any card oracle.json lacks, left out of the counts."""
import json, re, sys
from math import comb
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import ORACLE, decklist, front, is_land
from tables import table

COLOURS = "WUBRG"
TYPES = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}
FETCH = re.compile(r"search your library for ([^.]*)", re.I)
CURVE = [str(n) for n in range(7)] + ["7+"]

def colours(e, identity):
    """the colours of the identity e makes mana of, a fetch land's by the land types it searches for"""
    got = set(e.get("produced_mana") or [])
    if is_land(e):
        for want in FETCH.findall(front(e).get("oracle_text", "")):
            typed = {c for t, c in TYPES.items() if re.search(rf"\b{t}\b", want)}
            got |= typed or (set(identity) if "basic land card" in want else set())
    return got & set(identity)

def pips(e, colour): return front(e).get("mana_cost", "").count(f"{{{colour}}}")

def page(slug, commanders, rest):
    """the mana file's text from [(copies, oracle entry)] of the commanders and of the rest of the deck"""
    deck = commanders + rest
    identity = [c for c in COLOURS if any(c in e.get("color_identity", []) for _, e in commanders)]
    lands = [(n, e) for n, e in deck if is_land(e)]
    spells = [(n, e) for n, e in deck if not is_land(e)]
    count = lambda cards: sum(n for n, _ in cards)
    mean = sum(n * e.get("cmc", 0) for n, e in spells) / max(count(spells), 1)
    curve = [count((n, e) for n, e in spells if min(int(e.get("cmc", 0)), 7) == i) for i in range(8)]
    size, drawn = count(rest), count((n, e) for n, e in rest if is_land(e))
    odds = [f"{comb(drawn, k) * comb(size - drawn, 7 - k) / comb(size, 7):.0%}" if size >= 7 else "unknown"
            for k in (2, 3, 4)]
    rows = []
    for c in identity:
        sources = lambda cards: count((n, e) for n, e in cards if c in colours(e, identity))
        heavy = [(n, e) for n, e in spells if pips(e, c) >= 2]
        lowest = f"{min(e.get('cmc', 0) for _, e in heavy):g}" if heavy else "-"
        rows.append([c, *map(str, (sources(lands), sources(spells), sum(n * pips(e, c) for n, e in spells),
                                   count(heavy))), lowest])
    return "\n".join([f"# {slug}: mana", "",
                      "## Curve", table("| Lands | Nonlands | Mean mana value | " + " | ".join(CURVE) + " |",
                                        [[str(count(lands)), str(count(spells)), f"{mean:.1f}", *map(str, curve)]]), "",
                      "## Opening seven", table("| 2 lands | 3 lands | 4 lands |", [odds]), "",
                      "## Colours", table("| Colour | Land sources | Nonland sources | Pips | Cards with 2+ pips |"
                                          " Lowest mana value of those |", rows), ""])

def write(run, slug):
    cards = json.loads(ORACLE.read_text())["cards"]
    named = {f.casefold(): e for n, e in cards.items() for f in n.split(" // ")} | {n.casefold(): e for n, e in cards.items()}
    commanders, rest = decklist(slug)
    if missing := [n for _, n in commanders + rest if n.casefold() not in named]:
        print(f"{slug}: not in oracle.json:", ", ".join(missing))
    entries = lambda part: [(c, named[n.casefold()]) for c, n in part if n.casefold() in named]
    Path(run, f"{slug}-mana.md").write_text(page(slug, entries(commanders), entries(rest)))
