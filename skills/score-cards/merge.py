"""Merge the scorers' files to a deck's nonlands.md and lands.md: median, majority Role and spread flags.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score-cards/merge.py <run_dir> <slug> [card ...]
reads every <run_dir>/work-*/<slug>.md, one per scorer, its letter the folder name's last character, in letter
order, the deck title from output/decks/<slug>/plan.md's first `# ` heading (else list.txt's first line)
and the Adds and Cuts tables from output/decks/<slug>/nonlands.md and lands.md; writes <run_dir>/merged/<slug>/nonlands.md and lands.md, their
shape lines with the count of scorers and nonlands.md's Roles line, and, with two or more scorers,
<run_dir>/<slug>-flagged.md; prints the whole deck's shape line to stderr. A card's Role is the one most scorers
gave it, a tie going to the earliest letter's. One scorer's scores stand as they are: no spread, no flags.
Without cards, a card of list.txt the scorer files lack stops the run, naming it.
Given cards, only their rows are merged, a card the scorer files lack stopping the run, and the deck's existing
nonlands.md and lands.md are patched instead: each listed card's row replaced or inserted in the Cards
table in score order and its Adds row dropped, each card not in the list (a candidate) replaced or inserted in the
Adds table of the file its type belongs to, keeping the New and ~Price of its old Adds row, else "-"; the Shape
and Roles lines recomputed, every other line as it was. A table written without the Role column reads "-" for it."""
import re, sys, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import key, norm, decklist, lands, by_kind, KINDS, DECKS
from tables import split, join, cells, scores, adds, tail, shape, tally, deck_file, recount, table, ranked, ADDS
SPLIT = 3  # a card the scorers put this far apart is flagged

def patch(text, cards, adds, scored):
    """a deck file's text with these [card, score, role, note] rows in its Cards table and these [card, score, role,
    note, new, price] rows in its Adds table (made after Cards if it has none), each table in score order and each
    row in place of its card's old row, the other Adds rows of the scored names dropped and the Shape line recomputed,
    keeping the scorer count it carried; every other line as it was"""
    secs = split(text)
    if adds and "## Adds" not in dict(secs): secs.insert([h for h, _ in secs].index("## Cards") + 1, tail([], [], [])[0])
    sec = dict(secs)
    new = {key(r[0]): r for r in cards}
    cards = [new.pop(key(r[0]), r) for r in scores(sec["## Cards"])] + list(new.values())
    if "## Adds" in sec:
        lines = sec["## Adds"]
        at = [i for i, l in enumerate(lines) if l.startswith("|")]
        lines[at[0]:at[-1] + 1] = [table(ADDS, ranked([r for r in scores(lines) if key(r[0]) not in scored] + adds, True))]
    recount(sec, cards)
    return join(secs)

def parse(p):
    out, sec = {}, None
    for line in open(p):
        if line.startswith("## "): sec = {"## Nonlands":"nonlands","## Lands":"lands","## Adds":"adds"}.get(line.strip()); continue
        if sec:
            for c in cells([line]):
                if len(c) >= 4 and re.fullmatch(r"\d+", c[1]): out[norm(c[0])] = (c[0], int(c[1]), c[2], c[3], sec)
    return out

def whole(deck, rows, scorers):
    """{kind: text} of the deck's nonlands.md and lands.md written whole from this run's rows, the title from plan.md's
    first `# ` heading less `: plan` (list.txt's first line when it has none or there is no plan.md), the Adds and
    Cuts tables kept with this run's scores"""
    plan = deck / "plan.md"
    head = re.search(r"^# (.+)$", plan.read_text() if plan.exists() else "", re.M)
    title = re.sub(r":\s*plan\s*$", "", head[1]).strip() if head else norm((deck / "list.txt").read_text().splitlines()[0])
    old = [dict(split(p.read_text())) for p in (deck / f"{k}.md" for k in KINDS) if p.exists()]
    rest = {k: [] for k in KINDS}
    if any("## Adds" in o for o in old):  # research metadata and order stay; scores, add notes and cut scores are this run's
        land = lands()
        got = {norm(r[0]): r[1:4] for r in rows["adds"]}
        score = {key(r[0]): r[1] for k in KINDS for r in rows[k]}
        adds = by_kind([[r[0], *got.get(norm(r[0]), r[1:4]), *r[4:]] for o in old for r in scores(o.get("## Adds", []))], land)
        cuts = by_kind([[r[0], score.get(key(r[0]), r[1]), *r[2:]] for o in old for r in cells(o.get("## Cuts", []))], land)
        intro = [l for o in old for l in o.get("## Adds", []) if l.strip() and not l.startswith("|")]
        rest = {k: tail(intro if k == "nonlands" else [], adds[k], cuts[k]) for k in KINDS}
    return {k: deck_file(title, k, rows[k], rest[k], scorers) for k in KINDS}

def main():
    if len(sys.argv) < 3: sys.exit(__doc__)
    raw, slug, named = sys.argv[1], sys.argv[2], sys.argv[3:]
    want = {key(c).lower() for c in named}
    deck = DECKS / slug
    files = sorted(Path(raw).glob(f"work-*/{slug}.md"), key=lambda p: p.parent.name[-1])
    if not files: sys.exit(f"no scorer files {raw}/work-*/{slug}.md")
    letters, scorers = [p.parent.name[-1] for p in files], [parse(p) for p in files]
    rows = {"nonlands": [], "lands": [], "adds": []}
    flagged = []
    for k in sorted(set().union(*scorers)):
        got = [d.get(k) for d in scorers]
        sc = [g[1] for g in got if g]
        disp = next(g[0] for g in got if g)
        if named and key(disp).lower() not in want: continue
        med = round(statistics.median(sc))
        roles = [g[2] for g in got if g]
        note = max((g for g in got if g), key=lambda g: len(g[3]))[3]
        if max(sc) - min(sc) >= SPLIT: flagged.append((disp, sc, [g[3] if g else "" for g in got]))
        secs = [g[4] for g in got if g]
        rows[max(set(secs), key=secs.count)].append([disp, str(med), max(roles, key=roles.count), note])
    scored = {key(r[0]) for k in rows for r in rows[k]}
    listed = {key(n) for part in decklist(slug) for _, n in part}
    have = {s.lower() for s in scored}
    lacked = [c for c in named if key(c).lower() not in have] if named else sorted(listed - scored)
    if lacked: sys.exit(f"{slug}: not in the scorer files: {', '.join(lacked)}")
    if named:  # a card-only score, patched into the deck's files
        if not all((deck / f"{k}.md").exists() for k in KINDS): sys.exit(f"no {deck}/nonlands.md and lands.md to patch")
        old = {k: (deck / f"{k}.md").read_text() for k in KINDS}
        kept = {key(r[0]): r[4:6] for r in adds(deck)}
        candidates = by_kind([[*r, *kept.get(key(r[0]), ["-", "-"])] for k in rows for r in rows[k] if key(r[0]) not in listed],
                             lands())
        text = {k: patch(old[k], [r for r in rows[k] if key(r[0]) in listed], candidates[k], scored) for k in KINDS}
    else: text = whole(deck, rows, len(files))
    out = Path(raw) / "merged" / slug; out.mkdir(parents=True, exist_ok=True)
    every = [r for k in KINDS for r in scores(dict(split(text[k]))["## Cards"])]
    secs = split(text["nonlands"]); tally(secs, every); text["nonlands"] = join(secs)
    for k in KINDS: (out / f"{k}.md").write_text(text[k])
    line = f"{slug}: {shape(every, len(files))}"
    if len(files) > 1:
        Path(f"{raw}/{slug}-flagged.md").write_text(f"# {slug}: cards with spread >= {SPLIT}\n\n" + "".join(
            f"## {d}\nScores {'/'.join(letters)}: {sc}\n" + "".join(f"- {x}: {n}\n" for x, n in zip(letters, notes)) + "\n"
            for d, sc, notes in flagged))
        line += f" {len(flagged)} flagged"
    print(line, file=sys.stderr)

if __name__ == "__main__": main()
