"""Rebuild output/data/oracle.json from Scryfall for every card in output/decks/*/list.txt and in the
Adds table of every output/decks/*/nonlands.md and lands.md, each card with its Scryfall rulings (the comment
texts, oldest first) from Scryfall's bulk rulings file and its tags: the labels of its Scryfall functional tags and every
tag above them in the tag tree, from Scryfall's bulk oracle tags file, cached as output/data/oracle-tags.jsonl.gz and
downloaded again only when Scryfall's bulk index shows a newer one. Given card names, instead fetch each one oracle.json
lacks singly from Scryfall into it, with its rulings and its tags from the cached file, every other entry as it was.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/fetch_oracle.py ["Card Name" ...]"""
import gzip, json, os, re, sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from net import get, SCRYFALL
from project import card, write, ORACLE, DATA, DECKS
from tables import adds
API, BATCH = f"{SCRYFALL}/cards/collection", 75  # Scryfall's most names per collection request
KEEP = ["name", "oracle_id", "mana_cost", "cmc", "type_line", "oracle_text", "colors", "color_identity",
        "power", "toughness", "loyalty", "produced_mana"]
FACE = ["name", "mana_cost", "type_line", "oracle_text", "colors", "power", "toughness", "loyalty"]
TAGS = DATA / "oracle-tags.jsonl.gz"

def post(names):
    r = json.loads(get(API, {"identifiers": [{"name": n} for n in names]}))
    return r["data"], [x["name"] for x in r.get("not_found", [])]

def bulk():
    """Scryfall's bulk-data index: type -> its entry"""
    return {b["type"]: b for b in json.loads(get(f"{SCRYFALL}/bulk-data"))["data"]}

def rulings(index):
    """oracle_id -> the comment of each of its Scryfall rulings, oldest first"""
    out = {}
    for r in sorted(map(json.loads, gzip.decompress(get(index["rulings"]["jsonl_download_uri"])).splitlines()),
                    key=lambda r: r["published_at"]):
        out.setdefault(r["oracle_id"], []).append(r["comment"])
    return out

def tags(index=None):
    """oracle_id -> the labels of its functional tags and every tag above them, sorted, from the cached oracle tags file,
    {} with none; given Scryfall's bulk index, that file is downloaded first if the index shows a newer one (the cached
    copy's mtime is its updated_at)"""
    if index:
        b = index["oracle_tags"]; when = int(datetime.fromisoformat(b["updated_at"]).timestamp())  # whole seconds
        if not TAGS.exists() or TAGS.stat().st_mtime < when:
            replace(TAGS, get(b["jsonl_download_uri"])); os.utime(TAGS, (when, when))
    if not TAGS.exists(): return {}
    tree = {t["id"]: t for t in map(json.loads, gzip.decompress(TAGS.read_bytes()).splitlines()) if t["type"] == "oracle"}
    def lineage(i):
        """the labels of tag i and every tag above it, the bulk holding direct taggings only"""
        seen, todo = set(), [i]
        while todo:
            if (t := todo.pop()) in tree and t not in seen: seen.add(t); todo += tree[t]["parent_ids"] or []
        return {tree[t]["label"] for t in seen}
    out = {}
    for i, t in tree.items():
        labels = lineage(i)
        for g in t["taggings"]: out.setdefault(g["oracle_id"], set()).update(labels)
    return {o: sorted(labels) for o, labels in out.items()}

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

def replace(path, data):
    """data written whole to a temp file renamed over path, so a failed run leaves the old file"""
    tmp = path.with_suffix(".tmp")
    write(tmp, data)
    tmp.replace(path)

def save(oracle): replace(ORACLE, json.dumps(oracle, indent=1, sort_keys=True))

def add(names):
    """fetch each of names oracle.json, if any, lacks singly into it, with its rulings and tags; the names Scryfall has no
    card for"""
    oracle = json.loads(ORACLE.read_text()) if ORACLE.exists() else {"cards": {}}; missing = []; tagged = None
    for n in names:
        c = card(n, oracle["cards"])
        if c is None: missing.append(n)
        elif c not in oracle["cards"].values():
            tagged = tags() if tagged is None else tagged
            oracle["cards"][c["name"]] = {**entry(c), "rulings": c["rulings"], "tags": tagged.get(c.get("oracle_id"), [])}
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
    index = bulk(); said, tagged = rulings(index), tags(index)
    for e in out.values(): e["rulings"], e["tags"] = said.get(e.get("oracle_id"), []), tagged.get(e.get("oracle_id"), [])
    save({"cards": out})
    fronts = {n.split(" // ")[0] for n in out}
    print(len(names), "requested,", len(out), "saved; missing:", [n for n in names if n.split(" // ")[0] not in fronts])
    print("game changers:", sorted(n for n, e in out.items() if e.get("game_changer")))

if __name__ == "__main__":
    if len(sys.argv) == 1: rebuild()
    elif missing := add(sys.argv[1:]): sys.exit(f"not on Scryfall: {', '.join(missing)}")
