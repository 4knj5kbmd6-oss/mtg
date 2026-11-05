"""Apply every row of changes.md to its deck, so output/decks/<slug>/list.txt is the deck as the owner intends it.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/apply_changes.py
An In card not in the list is appended before any SIDEBOARD block (n copies from an "n copies" note, else 1) and its
Adds row in nonlands.md or lands.md moves to that file's Cards table. An Out card in the list loses one copy (all with
a copies note); once gone, its Cards and Cuts rows go too. A "to n copies" note sets the row's one card, In or Out, to
exactly n copies, its count changed in place where the list and Cards table hold it, added as an In card where they
do not, removed as an Out card at 0; a row naming two cards with it is reported and skipped. Both Shape lines are
recomputed, each keeping its scorer count, and so is nonlands.md's Roles line where it has one. Running it twice
changes nothing. Prints one line per changed deck: cards in or raised, cards out or lowered, and the deck's card count,
commander included and SIDEBOARD block left out, marked short or over when it is not 100."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import match, norm, decklist, KINDS, DECKS, CHANGES
from tables import split, join, cells, scores, recount, tally

def counted(name, n): return f"{name} ({n})" if n > 1 else name

def size(slug):
    """the deck's card count from its list.txt: 100, else marked as 99 (short 1) or 102 (over 2)"""
    n = sum(q for part in decklist(slug) for q, _ in part)
    return f"{n}" if n == 100 else f"{n} ({'short' if n < 100 else 'over'} {abs(n - 100)})"

def to(note):
    """n of a "to n copies" note, else None"""
    m = re.search(r"\bto\s+(\d+)\s+copies", note); return int(m.group(1)) if m else None

def apply_list(lines, rows):
    """lines of list.txt with rows applied in place; returns [(card, copies)] added or raised, [(card, copies left)]
    cut or lowered"""
    end = next((i for i, l in enumerate(lines) if l.strip() == "SIDEBOARD:"), len(lines))
    find = lambda name: next((i for i in range(end) if lines[i].strip() and match(name)(lines[i])), None)
    have = lambda i: int(lines[i].partition(" ")[0]) if i is not None else 0
    def put(name, n):
        """name at n copies, appended before any SIDEBOARD block when absent, removed at 0"""
        nonlocal end
        if (i := find(name)) is None:
            at = end
            while at > 0 and not lines[at - 1].strip(): at -= 1
            lines.insert(at, f"{n} {name}"); end += 1
        elif n: lines[i] = f"{n} {lines[i].partition(' ')[2]}"
        else: del lines[i]; end -= 1
    ins, outs = [], []
    for _, card_in, card_out, note in rows:
        if (want := to(note)) is not None:
            name = card_in or card_out; was = have(find(name))
            if name and want != was: put(name, want); (ins if want > was else outs).append((name, want))
            continue
        n = int(m.group(1)) if (m := re.search(r"(\d+)\s+copies", note)) else None
        if card_in and find(card_in) is None: put(card_in, 1 if n is None else n); ins.append((card_in, 1 if n is None else n))
        if card_out and (i := find(card_out)) is not None:
            left = 0 if n is not None else have(i) - 1
            put(card_out, left); outs.append((card_out, left))
    return ins, outs

def apply_scores(files, ins, outs):
    """{kind: text} of nonlands.md and lands.md with the applied rows moved, recounted in place or removed, and the
    tables recounted, nonlands.md's Roles line too where it has one"""
    secs = {k: split(t) for k, t in files.items()}
    sec = {k: dict((h, ls) for h, ls in s) for k, s in secs.items()}
    cards = {k: scores(s.get("## Cards", [])) for k, s in sec.items()}
    def drop(k, h, hit):
        if h in sec[k]: sec[k][h][:] = [l for l in sec[k][h] if not any(hit(c[0]) for c in cells([l]))]
    for name, n in ins + outs:
        hit = match(name)
        held = any(hit(r[0]) for rows in cards.values() for r in rows)
        for k in sec:
            if not n: cards[k] = [r for r in cards[k] if not hit(r[0])]; drop(k, "## Cuts", hit)
            elif held: cards[k] = [[counted(norm(r[0]), n), *r[1:]] if hit(r[0]) else r for r in cards[k]]
            elif row := next((r for r in scores(sec[k].get("## Adds", [])) if hit(r[0])), None):
                cards[k].append([counted(row[0], n), *row[1:4]]); drop(k, "## Adds", hit); held = True
    for k in sec: recount(sec[k], cards[k])
    if "## Roles" in sec.get("nonlands", {}): tally(secs["nonlands"], [r for rows in cards.values() for r in rows])
    return {k: join(s) for k, s in secs.items()}

def main():
    if not CHANGES.exists(): return
    decks = {}
    for c in cells(CHANGES.read_text().splitlines()):
        if len(c) < 3 or not c[0] or c[0] == "Deck": continue
        slug, card_in, card_out, note = (c + [""])[:4]
        if card_in and card_out and to(note) is not None: print(f"skip {slug}: {card_in} for {card_out}, \"{note}\" sets one card")
        else: decks.setdefault(slug, []).append((slug, card_in, card_out, note))
    for slug, rows in decks.items():
        deck = DECKS / slug
        if not (deck / "list.txt").exists(): print(f"skip {slug}: no {deck}/list.txt"); continue
        lines = (deck / "list.txt").read_text().split("\n")
        ins, outs = apply_list(lines, rows)
        if not ins and not outs: continue
        (deck / "list.txt").write_text("\n".join(lines))
        paths = {k: deck / f"{k}.md" for k in KINDS if (deck / f"{k}.md").exists()}
        for k, text in apply_scores({k: p.read_text() for k, p in paths.items()}, ins, outs).items(): paths[k].write_text(text)
        print(f"{slug}: in {'; '.join(counted(n, q) for n, q in ins) or '-'} | out {'; '.join(n for n, _ in outs) or '-'} | {size(slug)}")

if __name__ == "__main__": main()
