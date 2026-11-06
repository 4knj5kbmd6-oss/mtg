"""The project the scripts run in, the folder that holds output/: its paths, card names, deck lists and cards."""
import json, re, sys, urllib.parse
from pathlib import Path
from net import get, found, SCRYFALL, SEARCH
DECKS, DATA = Path("output/decks"), Path("output/data")
ORACLE, RULES, IMAGES = DATA / "oracle.json", DATA / "rules.txt", DATA / "images"
CHANGES, COLLECTION = Path("changes.md"), Path("collection.md")
KINDS = ("nonlands", "lands")
COUNT = r"\s*(?:\((\d+)\)|[x×]\s*(\d+))$"
NAMED = f"{SCRYFALL}/cards/named?exact="

def write(path, data):
    """data, text or bytes, written to path, its folder made first"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data) if isinstance(data, bytes) else path.write_text(data)

def key(name):
    """name for matching across files: no count or parenthetical, front face only"""
    return re.sub(r"^\d+\s+|\s*(\(.*\)|[x×]\s*\d+)$", "", name.strip()).split(" // ")[0].strip()

def match(name):
    """test for a list line or table cell naming this card, by front face"""
    k = key(name).lower(); return lambda s: key(s).lower() == k

def norm(n):
    n = re.sub(COUNT, "", n.strip()).strip(); return re.sub(r"^\d+\s+", "", n)

def copies(n):
    m = re.search(COUNT, n.strip()); return int(m.group(1) or m.group(2)) if m else 1

def decklist(slug):
    """([(copies, name)] of the commanders, [(copies, name)] of the rest) from output/decks/<slug>/list.txt, the
    commanders being the lines before its first blank line and its SIDEBOARD: block left out; no list.txt stops the
    run"""
    if not (path := DECKS / slug / "list.txt").exists(): sys.exit(f"no {path}")
    text = path.read_text().split("SIDEBOARD:")[0].strip()
    rows = lambda t: [(int(m[1]), m[2]) for l in t.splitlines() if (m := re.match(r"(\d+)\s+(.+)", l.strip()))]
    head, _, rest = text.partition("\n\n")
    return rows(head), rows(rest)

def listed():
    """every card name in a deck's list.txt, commanders and SIDEBOARD block included"""
    return {m.group(1) for f in DECKS.glob("*/list.txt") for line in f.read_text().splitlines()
            if (m := re.match(r"\d+ (.+)", line.strip()))}

def front(e): return (e.get("card_faces") or [e])[0]

def is_land(e): return "Land" in front(e).get("type_line", "").split()

def lands():
    """name -> whether its front face is a Land in oracle.json; a card not in it is a nonland"""
    fronts = {n.split(" // ")[0]: e for n, e in json.loads(ORACLE.read_text())["cards"].items()}
    return lambda name: is_land(fronts.get(key(name), {}))

def named():
    """oracle.json's cards by name and by each face's name, casefolded"""
    cards = json.loads(ORACLE.read_text())["cards"]
    faces = {f.casefold(): e for n, e in cards.items() for f in n.split(" // ")}
    return faces | {n.casefold(): e for n, e in cards.items()}

def field(label, text):
    """the text after each `- **<label>:**` bullet of text"""
    return re.findall(rf"^- \*\*{label}:\*\*[ \t]*(.*)$", text, re.M)

def cedh(slug):
    """whether output/decks/<slug>/plan.md carries `- **cEDH:** yes`, the deck built for the cEDH metagame"""
    plan = DECKS / slug / "plan.md"
    return plan.exists() and any(v.strip() == "yes" for v in field("cEDH", plan.read_text()))

def names(text, known):
    """the card names of text, separated by ; or by commas, a comma-separated run taken whole when it names a known
    card (known: casefolded names)"""
    out = []
    for chunk in text.split(";"):
        parts = [p.strip() for p in chunk.split(", ")]
        while parts:
            j = next((j for j in range(len(parts), 0, -1) if ", ".join(parts[:j]).casefold() in known), 1)
            out.append(", ".join(parts[:j])); parts = parts[j:]
    return [n for n in out if n]

def by_kind(rows, land):
    """{"nonlands": rows, "lands": rows}, split on whether a row's first cell names a land"""
    return {k: [r for r in rows if land(r[0]) == (k == "lands")] for k in KINDS}

def card(name, oracle):
    """name's oracle entry, else Scryfall's card with its rulings; None if Scryfall has no such card"""
    want = name.casefold()
    for matches in (lambda n: n == want, lambda n: n.split(" // ")[0] == want, lambda n: want in n.split(" // ")[1:]):
        for n, e in oracle.items():
            if matches(n.casefold()): return e
    if (c := found(NAMED + urllib.parse.quote(name))) is None: return None
    return {**c, "rulings": [r["comment"] for r in json.loads(get(c["rulings_uri"]))["data"]]}

def image_file(name):
    """output/data/images/<name>.jpg, Scryfall's normal image of name's earliest paper printing (front face of a
    double-faced card), fetched into it when missing; None if Scryfall has no such card"""
    path = IMAGES / f"{name}.jpg"
    if not path.exists():
        query = urllib.parse.quote(f'!"{name}" game:paper unique:prints order:released dir:asc')
        if (r := found(SEARCH + query)) is None: return None
        card = r["data"][0]
        write(path, get((card.get("image_uris") or card["card_faces"][0]["image_uris"])["normal"]))
    return path
