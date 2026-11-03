"""Rebuild output/data/oracle.json from Scryfall for every card in output/decks/*/list.txt and in the
Adds table of every output/decks/*/nonlands.md and lands.md, each card with its Scryfall rulings (the comment
texts, oldest first) from Scryfall's bulk rulings file. Given card names, instead fetch each one oracle.json
lacks singly from Scryfall into it, with its rulings, every other entry as it was.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch_oracle.py ["Card Name" ...]"""
import gzip, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from net import get, SCRYFALL
from project import card, write, ORACLE, DECKS
from tables import adds
API, BATCH = f"{SCRYFALL}/cards/collection", 75  # Scryfall's most names per collection request
KEEP = ["name", "oracle_id", "mana_cost", "cmc", "type_line", "oracle_text", "colors", "color_identity",
        "power", "toughness", "loyalty", "produced_mana"]
FACE = ["name", "mana_cost", "type_line", "oracle_text", "colors", "power", "toughness", "loyalty"]

def post(names):
    r = json.loads(get(API, {"identifiers": [{"name": n} for n in names]}))
    return r["data"], [x["name"] for x in r.get("not_found", [])]

def rulings():
    """oracle_id -> the comment of each of its Scryfall rulings, oldest first"""
    gz = next(b for b in json.loads(get(f"{SCRYFALL}/bulk-data"))["data"] if b["type"] == "rulings")["jsonl_download_uri"]
    out = {}
    for r in sorted(map(json.loads, gzip.decompress(get(gz)).splitlines()), key=lambda r: r["published_at"]):
        out.setdefault(r["oracle_id"], []).append(r["comment"])
    return out

def entry(c):
    e = {k: c[k] for k in KEEP if k in c}
    e["legalities"] = {"commander": c["legalities"].get("commander")}
    if c.get("game_changer"): e["game_changer"] = True
    if "card_faces" in c: e["card_faces"] = [{k: f[k] for k in FACE if k in f} for f in c["card_faces"]]
    e["related_tokens"] = sorted({p["name"] for p in c.get("all_parts", []) if p["component"] == "token"})
    return e

def card_names():
    """every card in a deck list or a deck's Adds table"""
    listed = {m.group(1) for f in DECKS.glob("*/list.txt") for line in f.read_text().splitlines()
              if (m := re.match(r"\d+ (.+)", line.strip()))}
    return sorted(listed | {r[0] for d in DECKS.glob("*") for r in adds(d)})

def save(oracle):
    """oracle.json written whole to a temp file renamed over it, so a failed run leaves the old file"""
    tmp = ORACLE.with_suffix(".tmp")
    write(tmp, json.dumps(oracle, indent=1, sort_keys=True))
    tmp.replace(ORACLE)

def add(names):
    """fetch each of names oracle.json, if any, lacks singly into it, with its rulings; the names Scryfall has no card for"""
    oracle = json.loads(ORACLE.read_text()) if ORACLE.exists() else {"cards": {}}; missing = []
    for n in names:
        c = card(n, oracle["cards"])
        if c is None: missing.append(n)
        elif c not in oracle["cards"].values(): oracle["cards"][c["name"]] = {**entry(c), "rulings": c["rulings"]}
    save(oracle)
    return missing

def rebuild():
    names = card_names()
    cards, missing = [], []
    for i in range(0, len(names), BATCH):
        got, nf = post(names[i:i + BATCH])
        cards += got; missing += nf
    retry = [n.split(" // ")[0] for n in missing if " // " in n]  # double-faced cards by front face
    if retry: cards += post(retry)[0]
    out = {c["name"]: entry(c) for c in cards}
    # a name that is also another card's face (Sign in Blood, the Omen) comes back only alone
    for n in names:
        if n not in out and n.split(" // ")[0] not in {k.split(" // ")[0] for k in out}:
            got, _ = post([n])
            out.update({c["name"]: entry(c) for c in got})
    said = rulings()
    for e in out.values(): e["rulings"] = said.get(e.get("oracle_id"), [])
    save({"cards": out})
    fronts = {n.split(" // ")[0] for n in out}
    print(len(names), "requested,", len(out), "saved; missing:", [n for n in names if n.split(" // ")[0] not in fronts])
    print("game changers:", sorted(n for n, e in out.items() if e.get("game_changer")))

if __name__ == "__main__":
    if len(sys.argv) == 1: rebuild()
    elif missing := add(sys.argv[1:]): sys.exit(f"not on Scryfall: {', '.join(missing)}")
