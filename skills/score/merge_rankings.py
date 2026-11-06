"""Merge the rankers' tables to rankings.md: per criterion the mean of the middle values, the Score recomputed, the
Ledger carried over and split criteria printed.
usage: python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/merge_rankings.py <run_dir>
reads every <run_dir>/rankings-<letter>.md, one per ranker, in letter order, each in the ranker agent's shape, a deck
known by the folder its Commander links to; writes <run_dir>/rankings.md in that shape: per deck each criterion the
mean, to one decimal, of the rankers' values sorted with the lowest and highest dropped while five or more remain
(the middle three of five, all of four or fewer), the Score round((mean - 1) / 8 * 100, 1) of the three, every other
cell and the deck's Ledger rows from the ranker whose Score for the deck is the median one (the lower middle when
even), rows by Score, strongest first, ties in the order of those rankers' tables; prints to stderr, per deck, the
criteria the rankers put SPLIT or more apart, each with its values in letter order. One ranker's file is copied as
it is."""
import re, shutil, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from tables import split, cells, table
SPLIT = 4  # a criterion the rankers put this far apart is printed
RANKINGS = "| # | Commander | Colours | Bracket | Score | Kill turn | Game Changers | Why | |"
CRITERIA = "| # | Commander | Speed | Resilience | Interaction |"
LEDGER = "| Commander | Criterion | Value | Count | Cards |"
NAMES = [c.strip() for c in CRITERIA.strip("|").split("|")][2:]

def parse(p):
    """{deck: (place, Rankings row, Criteria row, Ledger rows)} of one ranker's file, its rows as lists of cells"""
    secs = dict(split(p.read_text()))
    crit = {c[0]: c for c in cells(secs["## Criteria"])}
    ledger = [r for r in cells(secs.get("## Ledger", [])) if r[0] != "Commander"]
    name = lambda cell: re.sub(r"^\[(.*)\]\(.*\)$", r"\1", cell)
    return {deck(r[1]): (i, r, crit[r[0]], [l for l in ledger if l[0] == name(r[1])])
            for i, r in enumerate(cells(secs[None]))}

def deck(cell):
    m = re.search(r"decks/([^/)]+)", cell)
    return m.group(1) if m else cell

def middle(values):
    """the mean of values sorted, the lowest and highest dropped while five or more remain, to one decimal"""
    v = sorted(values)
    while len(v) >= 5: v = v[1:-1]
    return round(statistics.mean(v), 1)

def score(values): return round((statistics.mean(values) - 1) / 8 * 100, 1)

def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    run = Path(sys.argv[1])
    files = sorted(run.glob("rankings-?.md"))
    if not files: sys.exit(f"no ranker files {run}/rankings-<letter>.md")
    if len(files) == 1: return shutil.copy(files[0], run / "rankings.md")
    rankers = [parse(p) for p in files]
    rows = []
    for d in dict.fromkeys(d for r in rankers for d in r):
        got = [r[d] for r in rankers if d in r]
        place, row, crit, ledger = sorted(got, key=lambda g: float(g[1][4]))[(len(got) - 1) // 2]
        each = [[float(x) for x in v] for v in zip(*(g[2][2:] for g in got))]
        values = [middle(v) for v in each]
        rows.append((-score(values), place, row[:4] + [f"{score(values):.1f}"] + row[5:],
                     crit[:2] + [f"{v:.1f}" for v in values], ledger))
        apart = [f"{n} {'/'.join(f'{x:g}' for x in v)}" for n, v in zip(NAMES, each) if max(v) - min(v) >= SPLIT]
        if apart: print(f"{d}: split {', '.join(apart)}", file=sys.stderr)
    rows.sort(key=lambda r: r[:2])
    number = lambda r, i: [str(i)] + r[1:]
    (run / "rankings.md").write_text(
        "# Rankings\n\n" + table(RANKINGS, [number(r[2], i) for i, r in enumerate(rows, 1)])
        + "\n\n## Criteria\n\n" + table(CRITERIA, [number(r[3], i) for i, r in enumerate(rows, 1)])
        + "\n\n## Ledger\n\n" + table(LEDGER, [l for r in rows for l in r[4]]) + "\n")

if __name__ == "__main__": main()
