"""Cache every card of collection.md, the owner's | Card | Copies | table: its image in output/data/images/<name>.jpg
(by front face) and its entry in output/data/oracle.json, each fetched only when missing; no image with `images` false
in settings.json. Prints the count of cards, images fetched and oracle entries fetched. `decks` first adds at 1 copy
every card of every output/decks/*/list.txt that collection.md lacks, keeping its rows and their counts.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/collection/collection.py [decks]"""
import json, sys
from pathlib import Path
sys.path[:0] = [str(Path(__file__).resolve().parents[2] / d) for d in ("lib", "skills/sync")]
from fetch_oracle import add
from project import key, listed, image_file, write, COLLECTION, IMAGES, ORACLE
from settings import settings
from tables import owned, table
HEAD = "| Card | Copies |"

def seed():
    """add at 1 copy each deck card collection.md lacks, after its table's last row; the number added"""
    have = {key(n).lower() for n in owned()}
    new = sorted(n for n in listed() if key(n).lower() not in have)
    if not new: return 0
    lines = COLLECTION.read_text().splitlines() if COLLECTION.exists() else ["# Collection"]
    if not (rows := [i for i, l in enumerate(lines) if l.startswith("|")]):
        lines += ["", *table(HEAD, []).splitlines()]; rows = [len(lines) - 1]
    lines[rows[-1] + 1:rows[-1] + 1] = [f"| {n} | 1 |" for n in new]
    write(COLLECTION, "\n".join(lines) + "\n")
    return len(new)

def cache(names):
    """(images fetched, oracle entries fetched, names Scryfall has no card for) for names, each cache skipping a
    card it holds"""
    count = lambda: len(json.loads(ORACLE.read_text())["cards"]) if ORACLE.exists() else 0
    images, missing = 0, set()
    if settings()["images"]:
        for n in names:
            if (IMAGES / f"{key(n)}.jpg").exists(): continue
            if image_file(key(n)) is None: missing.add(n)
            else: images += 1
    before = count(); missing |= set(add(names))
    return images, count() - before, sorted(missing)

if __name__ == "__main__":
    if sys.argv[1:] not in ([], ["decks"]): sys.exit(__doc__)
    if sys.argv[1:]: print(f"{seed()} added from the decks")
    images, entries, missing = cache(names := owned())
    shown = f"{images} images fetched" if settings()["images"] else "no images (images is false)"
    print(f"{len(names)} cards, {shown}, {entries} oracle entries fetched")
    if missing: print("not on Scryfall:", ", ".join(missing))
