"""A deck's mana facts from its list and oracle.json, its <run_dir>/<slug>-mana.md, for facts.py and the mana skill.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/mana/mana.py <run_dir> <slug> [slug ...]
write() counts card copies of output/decks/<slug>/list.txt, commanders included: the lands; the nonlands; the cards the
plan's "- **Not cast:** Card, Card" line names, by name or either face, any other name printed; the nonlands' mean
mana value and curve; the chance of at least 2 lands by turn 2, 3 by turn 3 and 4 by turn 4 (odds.py) drawn from the
deck without its commanders; and per colour of the commanders' identity, the land sources, the sources needed and the
card that sets them, the nonland sources, the pips, the cards with two or more pips of it and the lowest mana value
among those. A nonland card with pips of a colour needs the fewest of the deck's lands to be sources of it that give it
at least that many among the cards seen by the turn of its mana value, 7 at most, 90% of the times at least its mana
value of lands are seen, or its pips when more; - when the deck has too few lands to see that many. The colour needs
the most any of its cards needs (ties: the lowest mana value, then by name). A chance or need is unknown when fewer of
the deck's cards are known than are seen by its turn. A card's colours are its produced_mana within the identity; a fetch land's are also those of
the basic land types it searches for, or every colour of the identity when it searches for a basic land card of no
type. Pips are the {W} {U} {B} {R} {G} symbols of the front face's cost. The recommendation (recommend.py) is the fewest
lands that cast the most spells on time in a ten-turn game, each spell weighted by its Score in the deck's nonlands.md,
the mean score when it has none, 1 when the deck has no scores: on time is on its due turn, its mana value or its pips
when more, or the turn it is drawn if later, with lands played one a turn and each ramp piece, a permanent that taps for
mana or a card that puts lands from the library onto the battlefield, a mana from the turn after both its mana value and
the turn it is drawn; modal double-faced lands count as lands, in Lands now too. A card not cast stays in the deck as a draw that
counts for nothing, neither land nor ramp, held fixed beside the ramp as the other spells scale with the lands. The split gives each colour of the
identity the number of those lands, each making one colour, that casts the most cards' pips on their due turn given that
turn's lands, and its share of them rounded to 5%. A real base meets the split when its lands match one to one the
split's sources, each making its source's colour, which holds when every set of colours has at least its sources' total
among the lands making one of them; every card's chance is then at least the split's. Prints any card oracle.json lacks,
left out of the counts."""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import DECKS, ORACLE, decklist, front, is_land, key
from tables import table, split as sections, scores
import odds, recommend

COLOURS = "WUBRG"
TYPES = {"Plains": "W", "Island": "U", "Swamp": "B", "Mountain": "R", "Forest": "G"}
FETCH = re.compile(r"search your library for ([^.]*)", re.I)
CURVE = [str(n) for n in range(7)] + ["7+"]
CHANCE = 0.9
REMINDER = re.compile(r"\([^)]*\)")
TAPS = re.compile(r"^[^:]*\{T\}[^:]*: Add ", re.M)
EXTRA = re.compile(r"\badds? an additional\b", re.I)
SEARCH = re.compile(r"search your library for [^.]*?\b(?:land|Plains|Island|Swamp|Mountain|Forest) cards?\b[^.]*"
                    r"\bonto the battlefield", re.I)
SPENDS = re.compile(r"\bsacrifice (?:a|any number of) lands?\b", re.I)
NOT_CAST = re.compile(r"^- \*\*Not cast:\*\*(.*)$", re.M)

def colours(e, identity):
    """the colours of the identity e makes mana of, a fetch land's by the land types it searches for"""
    got = set(e.get("produced_mana") or [])
    if is_land(e):
        for want in FETCH.findall(front(e).get("oracle_text", "")):
            typed = {c for t, c in TYPES.items() if re.search(rf"\b{t}\b", want)}
            got |= typed or (set(identity) if "basic land card" in want else set())
    return got & set(identity)

def pips(e, colour): return front(e).get("mana_cost", "").count(f"{{{colour}}}")

def land_drop(e):
    """whether e is played as a land: its front face is one, or its back face is and its front does not transform"""
    faces = e.get("card_faces") or []
    return is_land(e) or (len(faces) > 1 and "Land" in faces[1].get("type_line", "").split()
                          and "transform" not in faces[0].get("oracle_text", "").lower())

def ramp(e):
    """whether e, not a land drop, is ramp: a permanent that taps for mana without sacrificing or adds mana to a land's,
    or a card that puts lands from your library onto the battlefield without sacrificing lands"""
    if land_drop(e): return False
    text = REMINDER.sub("", front(e).get("oracle_text", ""))
    permanent = not {"Instant", "Sorcery"} & set(front(e).get("type_line", "").split())
    taps = any("Sacrifice" not in m[0] for m in TAPS.finditer(text)) or EXTRA.search(text)
    return bool(permanent and taps or SEARCH.search(text) and not SPENDS.search(text))

def due(e):
    """the turn e is due on curve: its mana value, or its pips when more, 1 at least"""
    return max(1, int(e.get("cmc", 0)), sum(pips(e, c) for c in COLOURS))

def turn(e): return min(int(e.get("cmc", 0)), 7)

def needed(e, colour, lands, size):
    """the fewest of the lands in a deck of size cards to be sources of the colour that give e its pips of it by its turn
    CHANCE of the times its lands are seen, None when none do"""
    want, seen = pips(e, colour), odds.seen(turn(e))
    least = max(int(e.get("cmc", 0)), want)
    return next((s for s in range(want, lands + 1)
                 if odds.given_lands(want, s, lands, size, seen, least) >= CHANCE), None)

def weights(slug):
    """name -> its card's Score in the deck's nonlands.md Cards table, the mean of the deck's scores for a card with
    none, 1 when the deck has none"""
    path, got = DECKS / slug / "nonlands.md", {}
    for row in scores(dict(sections(path.read_text())).get("## Cards", [])) if path.exists() else []:
        try: got[key(row[0]).casefold()] = float(row[1])
        except ValueError: pass
    mean = sum(got.values()) / len(got) if got else 1.0
    return lambda name: got.get(key(name).casefold(), mean)

def not_cast(slug, listed):
    """the oracle names of the cards the plan's Not cast line names, by name or either face, among listed (casefolded
    name or face -> oracle entry); prints any other name. A name may hold commas, so the longest run of comma-separated
    parts that names a card is taken"""
    path = DECKS / slug / "plan.md"
    line = NOT_CAST.search(path.read_text()) if path.exists() else None
    parts, got, unknown = [p.strip() for p in line[1].split(",")] if line else [], set(), []
    while parts:
        j = next((j for j in range(len(parts), 0, -1) if ", ".join(parts[:j]).casefold() in listed), 1)
        name, parts = ", ".join(parts[:j]), parts[j:]
        if name.casefold() in listed: got.add(listed[name.casefold()]["name"])
        elif name: unknown.append(name)
    if unknown: print(f"{slug}: Not cast, not in list.txt:", ", ".join(unknown))
    return got

def advice(identity, commanders, rest, weight, skipped):
    """the Recommendation table's row: the lands, the land drops now and each colour's share and sources, the skipped
    cards held in the deck as draws that count for nothing"""
    each = lambda cards: [e for n, e in cards for _ in range(n) if e["name"] not in skipped]
    card = lambda e: (weight(e["name"]), int(e.get("cmc", 0)), due(e), {c: pips(e, c) for c in identity if pips(e, c)})
    deck = each(rest)
    played = [(*card(e), ramp(e)) for e in deck if not land_drop(e)]
    led = [card(e) for e in each(commanders)]
    size, now = sum(n for n, _ in rest), sum(map(land_drop, deck))
    kept = size - len(deck)
    lands = recommend.lands(size, [(w, mv, d, r) for w, mv, d, _, r in played], [(w, mv, d) for w, mv, d, _ in led],
                            kept)
    if lands is None: return ["unknown", str(now), *["unknown"] * len(identity)]
    if not lands: return ["0", str(now), *["-"] * len(identity)]
    sources = recommend.split(lands, size, identity, [(w, r, d, need) for w, _, d, need, r in played],
                              [(w, d, need) for w, _, d, need in led], kept)
    share = recommend.shares(sources)
    return [str(lands), str(now), *(f"{share[c]}% ({sources[c]})" for c in identity)]

def page(slug, commanders, rest, weight, skipped):
    """the mana file's text from [(copies, oracle entry)] of the commanders and of the rest of the deck, name -> the
    card's weight, and the oracle names of the cards not cast"""
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
                      "## Curve", table("| Lands | Nonlands | Not cast | Mean mana value | " + " | ".join(CURVE) + " |",
                                        [[str(count(lands)), str(count(spells)),
                                          str(count((n, e) for n, e in deck if e["name"] in skipped)), f"{mean:.1f}",
                                          *map(str, curve)]]), "",
                      "## Lands", table("| 2 by turn 2 | 3 by turn 3 | 4 by turn 4 |", [on_curve]), "",
                      "## Colours", table("| Colour | Land sources | Sources needed | For | Nonland sources | Pips |"
                                          " Cards with 2+ pips | Lowest mana value of those |", rows), "",
                      "## Recommendation", table("| " + " | ".join(["Lands", "Lands now", *identity]) + " |",
                                                 [advice(identity, commanders, rest, weight, skipped)]), ""])

def write(run, slug):
    cards = json.loads(ORACLE.read_text())["cards"]
    named = {f.casefold(): e for n, e in cards.items() for f in n.split(" // ")} | {n.casefold(): e for n, e in cards.items()}
    commanders, rest = decklist(slug)
    if missing := [n for _, n in commanders + rest if n.casefold() not in named]:
        print(f"{slug}: not in oracle.json:", ", ".join(missing))
    entries = lambda part: [(c, named[n.casefold()]) for c, n in part if n.casefold() in named]
    listed = {f.casefold(): e for _, e in entries(commanders + rest) for f in [e["name"], *e["name"].split(" // ")]}
    Path(run, f"{slug}-mana.md").write_text(page(slug, entries(commanders), entries(rest), weights(slug),
                                                 not_cast(slug, listed)))

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    for slug in sys.argv[2:]: write(sys.argv[1], slug)

if __name__ == "__main__": main()
