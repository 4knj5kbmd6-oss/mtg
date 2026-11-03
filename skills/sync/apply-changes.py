"""Apply every row of changes.md to its deck, so output/decks/<slug>/list.txt is the deck as the owner intends it.
usage (from the folder that holds output/): python3 skills/sync/apply-changes.py
An In card not in the list is appended before any SIDEBOARD block (n copies from an "n copies" note, else 1) and its
Adds row in nonlands.md or lands.md moves to that file's Cards table. An Out card in the list loses one copy (all with
a copies note); once gone, its Cards and Cuts rows go too. Both Shape lines are recomputed, each keeping its scorer
count. Running it twice changes nothing. Prints one line per changed deck: cards in, cards out."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "score"))
from merge import split, join, cells, key, norm, table, ranked, shape, CARDS, KINDS

def match(name):
    """test for a list line or table cell naming this card"""
    k = key(name).lower(); return lambda s: key(s).lower() == k

def counted(name, n): return f"{name} ({n})" if n > 1 else name

def apply_list(lines, rows):
    """lines of list.txt with rows applied in place; returns [(In, copies)], [(Out, copies left)]"""
    end = next((i for i, l in enumerate(lines) if l.strip() == "SIDEBOARD:"), len(lines))
    find = lambda name: next((i for i in range(end) if lines[i].strip() and match(name)(lines[i])), None)
    ins, outs = [], []
    for _, card_in, card_out, note in rows:
        n = re.search(r"(\d+)\s+copies", note)
        if card_in and find(card_in) is None:
            at = end
            while at > 0 and not lines[at - 1].strip(): at -= 1
            lines.insert(at, f"{int(n.group(1)) if n else 1} {card_in}"); end += 1
            ins.append((card_in, int(n.group(1)) if n else 1))
        if card_out and (i := find(card_out)) is not None:
            qty, _, name = lines[i].partition(" "); left = 0 if n else int(qty) - 1
            if left: lines[i] = f"{left} {name}"
            else: del lines[i]; end -= 1
            outs.append((card_out, left))
    return ins, outs

def apply_scores(files, ins, outs):
    """{kind: text} of nonlands.md and lands.md with the applied rows moved, removed and recounted"""
    secs = {k: split(t) for k, t in files.items()}
    sec = {k: dict((h, ls) for h, ls in s) for k, s in secs.items()}
    cards = {k: cells(s.get("## Cards", [])) for k, s in sec.items()}
    def drop(k, h, hit):
        if h in sec[k]: sec[k][h][:] = [l for l in sec[k][h] if not any(hit(c[0]) for c in cells([l]))]
    for name, n in ins:
        hit = match(name)
        if any(hit(r[0]) for rows in cards.values() for r in rows): continue
        for k in sec:
            row = next((r for r in cells(sec[k].get("## Adds", [])) if hit(r[0])), None)
            if row: cards[k].append([counted(row[0], n), row[1], row[2]]); drop(k, "## Adds", hit); break
    for name, left in outs:
        hit = match(name)
        for k in sec:
            if left: cards[k] = [[counted(norm(r[0]), left), *r[1:]] if hit(r[0]) else r for r in cards[k]]
            else: cards[k] = [r for r in cards[k] if not hit(r[0])]; drop(k, "## Cuts", hit)
    for k in sec:
        if "## Cards" in sec[k]: sec[k]["## Cards"][:] = [table(CARDS, ranked(cards[k], True)), ""]
        if "## Shape" in sec[k]:
            n = re.search(r", (\d+) scorers?\.", "".join(sec[k]["## Shape"]))  # the scorer count the line carried
            sec[k]["## Shape"][:] = [shape(cards[k], n and int(n.group(1))), ""]
    return {k: join(s) for k, s in secs.items()}

def main():
    changes = Path("changes.md")
    if not changes.exists(): return
    decks = {}
    for c in cells(changes.read_text().splitlines()):
        if len(c) >= 3 and c[0] and c[0] != "Deck": decks.setdefault(c[0], []).append((c + [""])[:4])
    for slug, rows in decks.items():
        deck = Path("output/decks", slug)
        if not (deck / "list.txt").exists(): print(f"skip {slug}: no output/decks/{slug}/list.txt"); continue
        lines = (deck / "list.txt").read_text().split("\n")
        ins, outs = apply_list(lines, rows)
        if not ins and not outs: continue
        (deck / "list.txt").write_text("\n".join(lines))
        paths = {k: deck / f"{k}.md" for k in KINDS if (deck / f"{k}.md").exists()}
        for k, text in apply_scores({k: p.read_text() for k, p in paths.items()}, ins, outs).items(): paths[k].write_text(text)
        print(f"{slug}: in {'; '.join(counted(n, q) for n, q in ins) or '-'} | out {'; '.join(n for n, _ in outs) or '-'}")

if __name__ == "__main__": main()
