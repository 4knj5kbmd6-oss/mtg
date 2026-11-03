"""The project the scripts run in, the folder that holds output/: its paths, card names, deck lists and cards."""
import json, re, urllib.parse
from pathlib import Path
from net import get, found, SCRYFALL
DECKS, DATA = Path("output/decks"), Path("output/data")
ORACLE, RULES = DATA / "oracle.json", DATA / "rules.txt"
CHANGES = Path("changes.md")
KINDS = ("nonlands", "lands")
COUNT = r"\s*(?:\((\d+)\)|[x×]\s*(\d+))$"
NAMED = f"{SCRYFALL}/cards/named?exact="

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
    commanders being the lines before its first blank line and its SIDEBOARD: block left out"""
    text = (DECKS / slug / "list.txt").read_text().split("SIDEBOARD:")[0].strip()
    rows = lambda t: [(int(m[1]), m[2]) for l in t.splitlines() if (m := re.match(r"(\d+)\s+(.+)", l.strip()))]
    head, _, rest = text.partition("\n\n")
    return rows(head), rows(rest)

def front(e): return (e.get("card_faces") or [e])[0]

def is_land(e): return "Land" in front(e).get("type_line", "").split()

def lands():
    """name -> whether its front face is a Land in oracle.json; a card not in it is a nonland"""
    fronts = {n.split(" // ")[0]: e for n, e in json.loads(ORACLE.read_text())["cards"].items()}
    return lambda name: is_land(fronts.get(key(name), {}))

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
