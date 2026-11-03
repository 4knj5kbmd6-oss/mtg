"""Write each deck's changes sheet: an image of every suggested add and cut, as output/decks/<slug>/changes.png.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/upgrades/sheet.py [slug ...]   (no slug: every deck)
Four bands top to bottom, each a plain heading over its cards in table order: nonland adds, nonland cuts
(nonlands.md), land adds, land cuts (lands.md); a band with no rows is left out. The bands share one column
count, the one that makes the sheet's longer side shortest. A card's image is Scryfall's normal image of its
earliest paper printing (front face of a double-faced card), cached as output/data/images/<name>.jpg so a
later run fetches only new cards. A card Scryfall does not find is printed and left a blank slot."""
import sys, urllib.parse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from net import get, found, SEARCH
from project import key, write, KINDS, DECKS, DATA
from tables import split, cells
CACHE = DATA / "images"
BANDS = (("Nonland adds", "nonlands", "## Adds"), ("Nonland cuts", "nonlands", "## Cuts"),
         ("Land adds", "lands", "## Adds"), ("Land cuts", "lands", "## Cuts"))
W, H, GAP, HEAD = 488, 680, 12, 72
FONT = ImageFont.load_default(48)

def image(name):
    """the image of name's earliest paper printing, from the cache or fetched into it; None if Scryfall has no such card"""
    path = CACHE / f"{name}.jpg"
    if not path.exists():
        query = urllib.parse.quote(f'!"{name}" game:paper unique:prints order:released dir:asc')
        if (r := found(SEARCH + query)) is None: return None
        card = r["data"][0]
        write(path, get((card.get("image_uris") or card["card_faces"][0]["image_uris"])["normal"]))
    return Image.open(path).convert("RGB").resize((W, H))

def bands(slug):
    """[(heading, cards)] of the deck's bands that have rows, each card by its front face, in table order"""
    secs = {k: dict(split(p.read_text())) if (p := DECKS / slug / f"{k}.md").exists() else {} for k in KINDS}
    return [(head, names) for head, k, sec in BANDS if (names := [key(r[0]) for r in cells(secs[k].get(sec, []))])]

def rows(names, c): return -(-len(names) // c)

def size(bands, c):
    """(width, height) of the sheet with c columns: each band a heading, then its rows, GAP apart"""
    return c * (W + GAP) - GAP, sum(HEAD + rows(n, c) * (H + GAP) for _, n in bands) - GAP

def columns(bands):
    """the column count that makes the sheet's longer side shortest, so it stays roughly square; ties to less area"""
    return min(range(1, max(len(n) for _, n in bands) + 1),
               key=lambda c: (max(size(bands, c)), size(bands, c)[0] * size(bands, c)[1]))

def sheet(bands):
    """the bands drawn top to bottom, cards left to right; a band's last row may be short"""
    c = columns(bands); out = Image.new("RGB", size(bands, c), "white"); y = 0
    for head, names in bands:
        ImageDraw.Draw(out).text((0, y + HEAD // 2), head, fill="black", font=FONT, anchor="lm"); y += HEAD
        for i, n in enumerate(names):
            if (img := image(n)) is None: print(f"  not on Scryfall, left blank: {n}")
            else: out.paste(img, (i % c * (W + GAP), y + i // c * (H + GAP)))
        y += rows(names, c) * (H + GAP)
    return out

if __name__ == "__main__":
    for slug in sys.argv[1:] or sorted(p.name for p in DECKS.iterdir() if p.is_dir()):
        if not (b := bands(slug)): print(f"{slug}: no adds or cuts"); continue
        s = sheet(b); s.save(DECKS / slug / "changes.png")
        print(f"{slug}: {', '.join(f'{h.lower()} {len(n)}' for h, n in b)}; {columns(b)} columns, {s.width}x{s.height}")
