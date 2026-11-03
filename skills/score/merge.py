"""Merge the scorers' files to a deck's nonlands.md and lands.md: median and spread flags.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/merge.py <run_dir> <slug>
reads every <run_dir>/<slug>-<LETTER>.md, one per scorer, the deck title from output/decks/<slug>/plan.md
(from list.txt's first line when the plan is empty) and the Adds and Cuts tables from
output/decks/<slug>/nonlands.md and lands.md; writes <run_dir>/merged/<slug>/nonlands.md and lands.md, their
shape lines with the count of scorers, and, with two or more scorers, <run_dir>/<slug>-flagged.md; prints the
whole deck's shape line to stderr. One scorer's scores stand as they are: no spread, no flags."""
import re, sys, json, statistics, time, urllib.request
from pathlib import Path
CARDS = "| Card | Score | Note |"
ADDS = "| Card | Score | Note | New | ~Price |"
CUTS = "| Card | Score | Why it underperforms here |"
KINDS = ("nonlands", "lands")
COUNT = r"\s*(?:\((\d+)\)|[x×]\s*(\d+))$"
SCRYFALL, UA = "https://api.scryfall.com", "commander-deckhand"
last = 0.0

def get(url, body=None):
    """the response body to a GET of url, or a POST of body as JSON, at least 100 ms after the previous request"""
    global last
    time.sleep(max(0, last + 0.1 - time.monotonic()))
    head = {"User-Agent": UA, "Accept": "application/json;q=0.9,*/*;q=0.8"} | ({"Content-Type": "application/json"} if body else {})
    try: return urllib.request.urlopen(urllib.request.Request(url, body and json.dumps(body).encode(), head)).read()
    finally: last = time.monotonic()

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

def match(name):
    """test for a list line or table cell naming this card, by front face"""
    k = key(name).lower(); return lambda s: key(s).lower() == k

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
    if len(sys.argv) != 3: sys.exit(__doc__)
    raw, slug = sys.argv[1], sys.argv[2]
    deck = Path(f"output/decks/{slug}")
    plan = (deck / "plan.md").read_text().strip()
    title = re.sub(r"^#\s*|:\s*plan\s*$", "", plan.splitlines()[0]) if plan else norm((deck / "list.txt").read_text().splitlines()[0])
    files = sorted(Path(raw).glob(f"{slug}-[A-Z].md"))
    if not files: sys.exit(f"no scorer files {raw}/{slug}-<LETTER>.md")
    letters, scorers = [p.stem[-1] for p in files], [parse(p) for p in files]
    rows = {"nonlands": [], "lands": [], "adds": []}; flagged = []
    for k in sorted(set().union(*scorers)):
        got = [d.get(k) for d in scorers]; sc = [g[1] for g in got if g]
        disp = next(g[0] for g in got if g); med = round(statistics.median(sc))
        note = max((g for g in got if g), key=lambda g: len(g[2]))[2]
        if max(sc) - min(sc) >= 3: flagged.append((disp, sc, [g[2] if g else "" for g in got]))
        secs = [g[3] for g in got if g]; rows[max(set(secs), key=secs.count)].append([disp, str(med), note])
    cur = [p for p in (deck / f"{k}.md" for k in KINDS) if p.exists()]
    old = [dict(split(p.read_text())) for p in cur]
    rest = {k: [] for k in KINDS}
    if any("## Adds" in o for o in old):  # research metadata and order stay; scores, add notes and cut scores are this run's
        land = lands("output/data/oracle.json")
        got = {norm(r[0]): r[1:3] for r in rows["adds"]}
        score = {key(r[0]): r[1] for k in KINDS for r in rows[k]}
        adds = by_kind([[r[0], *got.get(norm(r[0]), r[1:3]), *r[3:]] for o in old for r in cells(o.get("## Adds", []))], land)
        cuts = by_kind([[r[0], score.get(key(r[0]), r[1]), *r[2:]] for o in old for r in cells(o.get("## Cuts", []))], land)
        intro = [l for o in old for l in o.get("## Adds", []) if l.strip() and not l.startswith("|")]
        rest = {k: tail(intro if k == "nonlands" else [], adds[k], cuts[k]) for k in KINDS}
    out = Path(raw) / "merged" / slug; out.mkdir(parents=True, exist_ok=True)
    for k in KINDS: (out / f"{k}.md").write_text(deck_file(title, k, rows[k], rest[k], len(files)))
    line = f"{slug}: {shape(rows['nonlands'] + rows['lands'], len(files))}"
    if len(files) > 1:
        Path(f"{raw}/{slug}-flagged.md").write_text(f"# {slug}: cards with spread >= 3\n\n" + "".join(
            f"## {d}\nScores {'/'.join(letters)}: {sc}\n" + "".join(f"- {x}: {n}\n" for x, n in zip(letters, notes)) + "\n"
            for d, sc, notes in flagged))
        line += f" {len(flagged)} flagged"
    print(line, file=sys.stderr)

if __name__ == "__main__": main()
