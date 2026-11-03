"""Run a Scryfall search and print its total count, Scryfall's warnings and the first 20 cards' names and type lines.
usage: python3 ${CLAUDE_PLUGIN_ROOT}/skills/scryfall/search.py "<query>"
A query Scryfall rejects (400) or that matches nothing (404) prints Scryfall's own error text and warnings and exits 1.
A warning names a term Scryfall ignored, which widens the results."""
import json, sys, urllib.parse
from pathlib import Path
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "score"))
from merge import get, SEARCH

SHOWN = 20

def answer(body):
    """a search response as the count line, a "Warning: " line for each of Scryfall's warnings and a
    "Name | Type line" line for each of its first 20 cards, or an error response as Scryfall's text for it (its
    details) and its warnings"""
    r = json.loads(body)
    warnings = [f"Warning: {w}" for w in r.get("warnings", [])]
    if r["object"] == "error": return "\n".join([r["details"]] + warnings)
    n, cards = r["total_cards"], r["data"][:SHOWN]
    head = f"{n} card{'s' * (n != 1)}" + (f", the first {len(cards)}:" if n > len(cards) else ":")
    return "\n".join([head] + warnings + [f"{c['name']} | {c['type_line']}" for c in cards])

if __name__ == "__main__":
    try: print(answer(get(SEARCH + urllib.parse.quote(sys.argv[1]))))
    except HTTPError as e:
        if e.code not in (400, 404): raise
        sys.exit(answer(e.read()))
