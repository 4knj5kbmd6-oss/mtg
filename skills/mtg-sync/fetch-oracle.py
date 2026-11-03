"""Rebuild output/data/oracle.json from Scryfall for every card in output/decks/*/list.txt and in the
Adds table of every output/decks/*/nonlands.md and lands.md.
usage (from the folder that holds output/): python3 skills/mtg-sync/fetch-oracle.py"""
import json, re, sys, time, urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mtg-score"))
from merge import split, cells, KINDS
API = "https://api.scryfall.com/cards/collection"
KEEP = ["name", "mana_cost", "cmc", "type_line", "oracle_text", "colors", "color_identity",
        "power", "toughness", "loyalty", "produced_mana"]
FACE = ["name", "mana_cost", "type_line", "oracle_text", "colors", "power", "toughness", "loyalty"]

def post(names):
    body = json.dumps({"identifiers": [{"name": n} for n in names]}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "mtg-oracle/1.0"})
    r = json.load(urllib.request.urlopen(req))
    time.sleep(0.12)
    return r["data"], [x["name"] for x in r.get("not_found", [])]

def entry(c):
    e = {k: c[k] for k in KEEP if k in c}
    e["legalities"] = {"commander": c["legalities"].get("commander")}
    if c.get("game_changer"): e["game_changer"] = True
    if "card_faces" in c: e["card_faces"] = [{k: f[k] for k in FACE if k in f} for f in c["card_faces"]]
    e["related_tokens"] = sorted({p["name"] for p in c.get("all_parts", []) if p["component"] == "token"})
    return e

def card_names():
    """every card in a deck list or a deck's Adds table"""
    listed = {m.group(1) for f in Path().glob("output/decks/*/list.txt") for line in f.read_text().splitlines()
              if (m := re.match(r"\d+ (.+)", line.strip()))}
    adds = {r[0] for k in KINDS for f in Path().glob(f"output/decks/*/{k}.md")
            for r in cells(dict(split(f.read_text())).get("## Adds", []))}
    return sorted(listed | adds)

if __name__ == "__main__":
    names = card_names()
    cards, missing = [], []
    for i in range(0, len(names), 75):
        got, nf = post(names[i:i + 75])
        cards += got; missing += nf
    retry = [n.split(" // ")[0] for n in missing if " // " in n]  # double-faced cards by front face
    if retry: cards += post(retry)[0]
    out = {c["name"]: entry(c) for c in cards}
    # a name that is also another card's face (Sign in Blood, the Omen) comes back only alone
    for n in names:
        if n not in out and n.split(" // ")[0] not in {k.split(" // ")[0] for k in out}:
            got, _ = post([n])
            out.update({c["name"]: entry(c) for c in got})
    json.dump({"fetched": date.today().isoformat(), "source": API, "cards": out},
              open("output/data/oracle.json", "w"), indent=1, sort_keys=True)
    fronts = {n.split(" // ")[0] for n in out}
    print(len(names), "requested,", len(out), "saved; missing:", [n for n in names if n.split(" // ")[0] not in fronts])
    print("game changers:", sorted(n for n, e in out.items() if e.get("game_changer")))
