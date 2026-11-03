"""Print each named card's oracle text and Scryfall rulings, for the judge's brief.
usage (from the folder that holds output/): python3 skills/mtg-rules/card.py "Card Name" [...]
A name matches output/data/oracle.json case-insensitively, as the full name or either face of a Front // Back
card; a card not there is fetched singly from Scryfall by exact name, with its rulings."""
import json, sys, urllib.parse, urllib.request
from urllib.error import HTTPError
from pathlib import Path

ORACLE = Path("output/data/oracle.json")
NAMED = "https://api.scryfall.com/cards/named?exact="

def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "mtg-rules/1.0"})
    return json.load(urllib.request.urlopen(req))

def card(name, oracle):
    """name's oracle entry, else Scryfall's card with its rulings; None if Scryfall has no such card"""
    want = name.casefold()
    for n, e in oracle.items():
        if want in (n.casefold(), *n.casefold().split(" // ")): return e
    try: c = get(NAMED + urllib.parse.quote(name))
    except HTTPError as e:
        if e.code == 404: return None
        raise
    return {**c, "rulings": [r["comment"] for r in get(c["rulings_uri"])["data"]]}

def text(c):
    """each face's name and cost, type and stats, and oracle text, then the rulings"""
    lines = []
    for f in c.get("card_faces", [c]):
        stats = f"{f['power']}/{f['toughness']}" if "power" in f else f"loyalty {f['loyalty']}" if "loyalty" in f else ""
        lines += [f"{f['name']} {f.get('mana_cost', '')}".rstrip(), f"{f['type_line']} {stats}".rstrip(), f.get("oracle_text", "")]
    lines += ["Rulings:", *(f"- {r}" for r in c["rulings"])] if c["rulings"] else ["Rulings: none"]
    return "\n".join(l for l in lines if l)

if __name__ == "__main__":
    oracle = json.loads(ORACLE.read_text())["cards"] if ORACLE.exists() else {}
    found = {n: card(n, oracle) for n in sys.argv[1:]}
    print("\n\n".join(text(c) for c in found.values() if c))
    missing = [n for n, c in found.items() if not c]
    if missing: sys.exit(f"not on Scryfall: {', '.join(missing)}")
