"""Write output/decks/<slug>/list.txt from a pasted decklist or a .txt export (Moxfield, Archidekt, MTGO or Arena text).
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/import.py <slug> [file]   (no file: read stdin)
Counts, set codes, collector numbers, foil marks and categories are stripped. The commander is a Commander section
(up to the next blank line) or category, else a lone block of one or two cards set apart by a blank line at the start or
end of the list. A Sideboard or Companion section becomes the SIDEBOARD: block; maybeboards are left out. Prints the
card count and every line it could not parse; those lines are not written."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "score"))
from merge import DECKS

SECTIONS = {"commander": "commander", "commanders": "commander", "deck": "main", "main": "main", "mainboard": "main",
            "sideboard": "side", "companion": "side", "maybeboard": None, "considering": None, "tokens": None, "about": "about"}
HEADER = re.compile(r"(?://|#)?\s*([a-z]+)\s*:?\s*(?:\(\d+\))?", re.I)
CARD = re.compile(r"(\d+)[xX]?\s+(.+)")

def card(text):
    """(count, name, tags) from a card line, or None; tags are the lowercased Archidekt categories"""
    if not (m := CARD.fullmatch(text)): return None
    name, tags = m.group(2), []
    for found in re.findall(r"\[([^\]]*)\]|\^([^^]*)\^", name):
        tags += [re.sub(r"\{.*?\}", "", t).strip().lower() for t in ",".join(found).split(",")]
    name = re.sub(r"\[[^\]]*\]|\^[^^]*\^|\*[A-Z]+\*", " ", name)
    name = re.sub(r"\s+\([A-Za-z0-9]{2,6}\)(\s+\S+)?\s*$", "", name.strip())
    name = " ".join(name.split())
    return (int(m.group(1)), name, tags) if name else None

def parse(text):
    """{"commander", "main", "side"}: {name: count} each, and the lines not parsed"""
    boards = {"commander": {}, "main": {}, "side": {}}
    loose, block, section, bad = [], [], "loose", []
    for line in text.lstrip("\ufeff").splitlines():
        line = line.strip()
        if not line:  # a blank line ends a block of loose cards and a Commander or About section
            if block: loose.append(block); block = []
            if section in ("commander", "about"): section = "loose"
            continue
        if (h := HEADER.fullmatch(line)) and h.group(1).lower() in SECTIONS:
            section = SECTIONS[h.group(1).lower()]; continue
        if section in (None, "about"): continue
        if not (c := card(line)): bad.append(line); continue
        n, name, tags = c
        board = next((b for t, b in (("commander", "commander"), ("maybeboard", None), ("sideboard", "side")) if t in tags), section)
        if board == "loose": block.append((n, name))
        elif board: boards[board][name] = boards[board].get(name, 0) + n
    if block: loose.append(block)
    if not boards["commander"] and loose and (len(loose) > 1 or boards["main"]):
        lone = next((b for b in (loose[0], loose[-1]) if len(b) <= 2), None)
        if lone: loose.remove(lone); boards["commander"] = dict((name, n) for n, name in lone)
    for b in loose:
        for n, name in b: boards["main"][name] = boards["main"].get(name, 0) + n
    return boards, bad

def listing(boards):
    """list.txt text: commander, blank line, the rest by name, optional SIDEBOARD: block"""
    rows = lambda b: [f"{n} {name}" for name, n in sorted(boards[b].items(), key=lambda e: e[0].casefold())]
    lines = (rows("commander") + [""] if boards["commander"] else []) + rows("main") + [""]
    if boards["side"]: lines += ["SIDEBOARD:"] + rows("side") + [""]
    return "\n".join(lines)

def main():
    if len(sys.argv) not in (2, 3): sys.exit(__doc__)
    slug = sys.argv[1]
    boards, bad = parse(open(sys.argv[2]).read() if len(sys.argv) == 3 else sys.stdin.read())
    deck = DECKS / slug
    deck.mkdir(parents=True, exist_ok=True)
    (deck / "list.txt").write_text(listing(boards))
    count = lambda b: sum(boards[b].values())
    print(f"{slug}: {count('commander') + count('main')} cards, {count('commander')} of them commander"
          + (f", {count('side')} in the sideboard" if boards["side"] else ""))
    if not boards["commander"]: print("no commander found: put it first, set apart by a blank line, and rerun")
    for line in bad: print(f"not parsed: {line}")

if __name__ == "__main__": main()
