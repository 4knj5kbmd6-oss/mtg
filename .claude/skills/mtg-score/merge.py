"""Merge three scorers' files to a deck's nonlands.md and lands.md: median, spread flags, optional arbitration.
usage (repo root): python3 .claude/skills/mtg-score/merge.py <run_dir> <slug> [arb.json]
reads <run_dir>/<slug>-A.md, -B.md, -C.md, the deck title from output/decks/<slug>/plan.md and the
Adds and Cuts tables from output/decks/<slug>/nonlands.md and lands.md (or a legacy scores.md);
writes <run_dir>/merged/<slug>/nonlands.md and lands.md and <run_dir>/<slug>-flagged.md; prints the
whole deck's shape line to stderr. The deck-file helpers here are shared with mtg-upgrades/apply.py."""
import re, sys, json, statistics
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
ADDS = "| Card | Score | Note | New | ~Price |"
CUTS = "| Card | Score | Why it underperforms here |"
KINDS = ("nonlands", "lands")
COUNT = r"\s*(?:\((\d+)\)|[x×]\s*(\d+))$"

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

def key(name):
    """name for matching across files: no count or parenthetical, front face only"""
    return re.sub(r"^\d+\s+|\s*(\(.*\)|[x×]\s*\d+)$", "", name.strip()).split(" // ")[0].strip()

def table(head, rows):
    return "\n".join([head, "|" + "---|" * (head.count("|") - 1)] + ["| " + " | ".join(r) + " |" for r in rows])

def ranked(rows, desc):
    """by the Score column, ties in the given order, unscored ("-") last"""
    return sorted(rows, key=lambda r: (not r[1].isdigit(), (-1 if desc else 1) * int(r[1]) if r[1].isdigit() else 0))

def tail(intro, adds, cuts):
    """the Adds (score descending) and Cuts (score ascending) sections"""
    return [["## Adds", intro + ["", table(ADDS, ranked(adds, True)), ""]],
            ["## Cuts", [table(CUTS, ranked(cuts, False)), ""]]]

def lands(oracle):
    """name -> whether its front face is a Land in the oracle.json at that path; a card not in it is a nonland"""
    front = {n.split(" // ")[0]: (e.get("card_faces") or [e])[0].get("type_line", "")
             for n, e in json.load(open(oracle))["cards"].items()}
    return lambda name: "Land" in front.get(key(name), "").split()

def by_kind(rows, land):
    """{"nonlands": rows, "lands": rows}, split on whether a row's first cell names a land"""
    return {k: [r for r in rows if land(r[0]) == (k == "lands")] for k in KINDS}

def shape(cards):
    """the shape line of [card, score, ...] rows, by card copy"""
    s = [int(r[1]) for r in cards for _ in range(copies(r[0]))]
    return (f"10: {sum(x==10 for x in s)} / 8-9: {sum(8<=x<=9 for x in s)} / 5-7: {sum(5<=x<=7 for x in s)}"
            f" / 4 or below: {sum(x<=4 for x in s)}, mean {sum(s)/max(len(s), 1):.1f} (by card copy).")

def deck_file(title, kind, cards, rest):
    """nonlands.md or lands.md: the Cards table, rest (its Adds and Cuts sections, if any), the Shape line"""
    return join([[None, [f"# {title}: {kind}", ""]], ["## Cards", [table("| Card | Score | Note |", ranked(cards, True)), ""]],
                 *rest, ["## Shape", [shape(cards), ""]]])

def norm(n):
    n = re.sub(COUNT, "", n.strip()).strip(); return re.sub(r"^\d+\s+", "", n)
def copies(n):
    m = re.search(COUNT, n.strip()); return int(m.group(1) or m.group(2)) if m else 1
def parse(p):
    out, sec = {}, None
    for line in open(p):
        if line.startswith("## "): sec = {"## Nonlands":"nonlands","## Lands":"lands","## Adds":"adds"}.get(line.strip()); continue
        if sec:
            for c in cells([line]):
                if len(c) >= 3 and re.fullmatch(r"\d+", c[1]): out[norm(c[0])] = (c[0], int(c[1]), c[2], sec)
    return out

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    raw, slug = sys.argv[1], sys.argv[2]
    arb = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
    deck = ROOT / f"output/decks/{slug}"
    title = re.sub(r"^#\s*|:\s*plan\s*$", "", (deck / "plan.md").read_text().splitlines()[0])
    A, B, C = (parse(f"{raw}/{slug}-{x}.md") for x in "ABC")
    rows = {"nonlands": [], "lands": [], "adds": []}; flagged = []
    for k in sorted(set(A) | set(B) | set(C)):
        got = [d.get(k) for d in (A, B, C)]; sc = [g[1] for g in got if g]
        disp = next(g[0] for g in got if g); med = int(statistics.median(sc)) if len(sc) == 3 else round(sum(sc)/len(sc))
        note = max((g for g in got if g), key=lambda g: len(g[2]))[2]
        if k in arb: med, note = arb[k]["score"], arb[k]["note"]
        elif max(sc) - min(sc) >= 3: flagged.append((disp, sc, [g[2] if g else "" for g in got]))
        secs = [g[3] for g in got if g]; rows[max(set(secs), key=secs.count)].append([disp, str(med), note])
    cur = [p for p in (deck / f"{k}.md" for k in KINDS) if p.exists()] or [p for p in [deck / "scores.md"] if p.exists()]
    old = [dict(split(p.read_text())) for p in cur]
    rest = {k: [] for k in KINDS}
    if any("## Adds" in o for o in old):  # research metadata and order stay; scores, add notes and cut scores are this run's
        land = lands(ROOT / "output/data/oracle.json")
        got = {norm(r[0]): r[1:3] for r in rows["adds"]}
        score = {key(r[0]): r[1] for k in KINDS for r in rows[k]}
        adds = by_kind([[r[0], *got.get(norm(r[0]), r[1:3]), *r[3:]] for o in old for r in cells(o.get("## Adds", []))], land)
        cuts = by_kind([[r[0], score.get(key(r[0]), r[1]), *r[2:]] for o in old for r in cells(o.get("## Cuts", []))], land)
        intro = [l for o in old for l in o.get("## Adds", []) if l.strip() and not l.startswith("|")]
        rest = {k: tail(intro if k == "nonlands" else [], adds[k], cuts[k]) for k in KINDS}
    out = Path(raw) / "merged" / slug; out.mkdir(parents=True, exist_ok=True)
    for k in KINDS: (out / f"{k}.md").write_text(deck_file(title, k, rows[k], rest[k]))
    with open(f"{raw}/{slug}-flagged.md", "w") as f:
        f.write(f"# {slug}: cards with spread >= 3\n\n" + "".join(f"## {d}\nScores A/B/C: {sc}\n- A: {n[0]}\n- B: {n[1]}\n- C: {n[2]}\n\n" for d, sc, n in flagged))
    print(f"{slug}: {shape(rows['nonlands'] + rows['lands'])} {len(flagged)} flagged", file=sys.stderr)

if __name__ == "__main__": main()
