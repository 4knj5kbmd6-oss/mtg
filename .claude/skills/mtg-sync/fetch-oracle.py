"""Rebuild output/data/oracle.json from Scryfall for every card in output/decks/*/list.txt.
usage: python3 .claude/skills/mtg-sync/fetch-oracle.py"""
import json, re, time, urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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

names = sorted({m.group(1) for f in ROOT.glob("output/decks/*/list.txt") for line in f.read_text().splitlines()
                if (m := re.match(r"\d+ (.+)", line.strip()))})
cards, missing = [], []
for i in range(0, len(names), 75):
    got, nf = post(names[i:i + 75])
    cards += got; missing += nf
retry = [n.split(" // ")[0] for n in missing if " // " in n]  # double-faced cards by front face
if retry: cards += post(retry)[0]
out = {c["name"]: entry(c) for c in cards}
json.dump({"fetched": date.today().isoformat(), "source": API, "cards": out},
          open(ROOT / "output/data/oracle.json", "w"), indent=1, sort_keys=True)
fronts = {n.split(" // ")[0] for n in out}
print(len(names), "requested,", len(out), "saved; missing:", [n for n in names if n.split(" // ")[0] not in fronts])
print("game changers:", sorted(n for n, e in out.items() if e.get("game_changer")))
