"""The Markdown of a deck's nonlands.md and lands.md: sections, tables and the Shape line."""
import re
from project import copies, KINDS
CARDS = "| Card | Score | Note |"
ADDS = "| Card | Score | Note | New | ~Price |"
CUTS = "| Card | Score | Why it underperforms here |"

def split(text):
    """[heading, lines] pairs, the title block first under heading None; join() undoes it"""
    out = [[None, []]]
    for line in text.split("\n"):
        if line.startswith("## "): out.append([line, []])
        else: out[-1][1].append(line)
    return out

def join(secs): return "\n".join(l for h, ls in secs for l in ([h] if h else []) + ls)

def cells(lines):
    """data rows of the tables in lines, as lists of cells"""
    return [[c.strip() for c in l.strip().strip("|").split("|")] for l in lines
            if l.startswith("|") and not re.match(r"^\|\s*(-+|Card|#)\s*\|", l)]

def adds(deck):
    """the Adds rows, as lists of cells, of the deck folder's nonlands.md and lands.md that exist"""
    return [r for k in KINDS if (p := deck / f"{k}.md").exists() for r in cells(dict(split(p.read_text())).get("## Adds", []))]

def table(head, rows):
    return "\n".join([head, "|" + "---|" * (head.count("|") - 1)] + ["| " + " | ".join(r) + " |" for r in rows])

def ranked(rows, desc):
    """by the Score column, ties in the given order, unscored ("-") last"""
    return sorted(rows, key=lambda r: (not r[1].isdigit(), (-1 if desc else 1) * int(r[1]) if r[1].isdigit() else 0))

def tail(intro, adds, cuts):
    """the Adds (score descending) and Cuts (score ascending) sections"""
    return [["## Adds", intro + ["", table(ADDS, ranked(adds, True)), ""]],
            ["## Cuts", [table(CUTS, ranked(cuts, False)), ""]]]

def shape(cards, scorers=None):
    """the shape line of [card, score, ...] rows, by card copy, unscored ("-") rows left out; with the
    count of scorers when given"""
    s = [int(r[1]) for r in cards if r[1].isdigit() for _ in range(copies(r[0]))]
    by = f", {scorers} scorer{'s' * (scorers != 1)}" if scorers else ""
    return (f"10: {sum(x==10 for x in s)} / 8-9: {sum(8<=x<=9 for x in s)} / 5-7: {sum(5<=x<=7 for x in s)}"
            f" / 4 or below: {sum(x<=4 for x in s)}, mean {sum(s)/max(len(s), 1):.1f} (by card copy){by}.")

def deck_file(title, kind, cards, rest, scorers):
    """nonlands.md or lands.md: the Cards table, rest (its Adds and Cuts sections, if any), the Shape line"""
    return join([[None, [f"# {title}: {kind}", ""]], ["## Cards", [table(CARDS, ranked(cards, True)), ""]],
                 *rest, ["## Shape", [shape(cards, scorers), ""]]])

def recount(sec, cards):
    """sec, a deck file's {heading: lines}, with its Cards table rewritten from these rows and its Shape line
    recomputed, keeping the scorer count it carried"""
    if "## Cards" in sec: sec["## Cards"][:] = [table(CARDS, ranked(cards, True)), ""]
    if "## Shape" in sec:
        n = re.search(r", (\d+) scorers?\.", "".join(sec["## Shape"]))
        sec["## Shape"][:] = [shape(cards, n and int(n.group(1))), ""]
