"""The Markdown of a deck's nonlands.md and lands.md: sections, tables and the Shape and Roles lines.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/lib/tables.py <slug>
prints the card names of the deck's Adds tables, one per line, and nothing else of its files."""
import re, sys
from collections import Counter
from project import copies, KINDS, DECKS
CARDS = "| Card | Score | Role | Note |"
ADDS = "| Card | Score | Role | Note | New | ~Price |"
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

def scores(lines):
    """data rows of the Cards or Adds table in lines, as lists of cells, "-" for the Role of a table written without
    that column"""
    old = "| Role |" not in next((l for l in lines if l.startswith("| Card |")), "| Role |")
    return [r[:2] + ["-"] + r[2:] if old else r for r in cells(lines)]

def adds(deck):
    """the Adds rows, as lists of cells, of the deck folder's nonlands.md and lands.md that exist"""
    return [r for k in KINDS if (p := deck / f"{k}.md").exists() for r in scores(dict(split(p.read_text())).get("## Adds", []))]

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

def roles(cards):
    """the Roles line of [card, score, role, ...] rows, by card copy, count descending, ties by name, the land role
    last as lands; unscored ("-") roles left out"""
    n = Counter()
    for r in cards:
        if r[2] != "-": n[r[2]] += copies(r[0])
    land = n.pop("land", 0)
    return " · ".join([f"{k} {v}" for k, v in sorted(n.items(), key=lambda kv: (-kv[1], kv[0]))] + [f"lands {land}"] * bool(land))

def tally(secs, cards):
    """secs, nonlands.md's [heading, lines] pairs, with its Roles section (made after Shape if it has none) set to the
    Roles line of cards, both files' Cards rows"""
    heads = [h for h, _ in secs]
    if "## Roles" not in heads: secs.insert(heads.index("## Shape") + 1 if "## Shape" in heads else len(secs), ["## Roles", []])
    dict(secs)["## Roles"][:] = [roles(cards), ""]

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

if __name__ == "__main__":
    if len(sys.argv) != 2: sys.exit(__doc__)
    for r in adds(DECKS / sys.argv[1]): print(r[0])
