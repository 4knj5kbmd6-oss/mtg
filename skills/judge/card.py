"""Print each named card's oracle text and Scryfall rulings, for the judge agent.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/card.py "Card Name" [...]
A name matches output/data/oracle.json case-insensitively, as a full name, else the front face of a Front // Back
card, else its back face; a card not there is fetched singly from Scryfall by exact name, with its rulings."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import card, ORACLE

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
    got = {n: card(n, oracle) for n in sys.argv[1:]}
    print("\n\n".join(text(c) for c in got.values() if c))
    missing = [n for n, c in got.items() if not c]
    if missing: sys.exit(f"not on Scryfall: {', '.join(missing)}")
