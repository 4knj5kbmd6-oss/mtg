"""Merge three scorers' files to one: median, spread flags, optional arbitration.
usage (repo root): python3 .claude/skills/mtg-score/merge.py <run_dir> <slug> [arb.json] > merged.md
reads <run_dir>/<slug>-A.md, -B.md, -C.md and the deck title from output/decks/<slug>/plan.md;
writes <run_dir>/<slug>-flagged.md; prints the shape line to stderr"""
import re, sys, json, statistics
from pathlib import Path
if len(sys.argv) < 3: sys.exit(__doc__)
ROOT = Path(__file__).resolve().parents[3]
raw, slug = sys.argv[1], sys.argv[2]
arb = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
title = re.sub(r"^#\s*|:\s*plan\s*$", "", (ROOT / f"output/decks/{slug}/plan.md").read_text().splitlines()[0])
COUNT = r"\s*(?:\((\d+)\)|[x×]\s*(\d+))$"
def norm(n):
    n = re.sub(COUNT, "", n.strip()).strip(); return re.sub(r"^\d+\s+", "", n)
def copies(n):
    m = re.search(COUNT, n.strip()); return int(m.group(1) or m.group(2)) if m else 1
def parse(p):
    out, sec = {}, None
    for line in open(p):
        if line.startswith("## "): sec = {"## Nonlands":"nonlands","## Lands":"lands","## Recommended adds":"adds"}.get(line.strip()); continue
        if sec and line.startswith("|") and not re.match(r"^\|\s*(-|Card)", line):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            if len(c) >= 3 and re.fullmatch(r"\d+", c[1]): out[norm(c[0])] = (c[0], int(c[1]), c[2], sec)
    return out
A, B, C = (parse(f"{raw}/{slug}-{x}.md") for x in "ABC")
rows = {"nonlands": [], "lands": [], "adds": []}; flagged = []
for k in sorted(set(A) | set(B) | set(C)):
    got = [d.get(k) for d in (A, B, C)]; sc = [g[1] for g in got if g]
    disp = next(g[0] for g in got if g); med = int(statistics.median(sc)) if len(sc) == 3 else round(sum(sc)/len(sc))
    note = max((g for g in got if g), key=lambda g: len(g[2]))[2]
    if k in arb: med, note = arb[k]["score"], arb[k]["note"]
    elif max(sc) - min(sc) >= 3: flagged.append((disp, sc, [g[2] if g else "" for g in got]))
    secs = [g[3] for g in got if g]; rows[max(set(secs), key=secs.count)].append((med, disp, note))
def table(s): return "| Card | Score | Note |\n|---|---|---|\n" + "\n".join(f"| {d} | {m} | {n} |" for m, d, n in sorted(rows[s], key=lambda r: -r[0]))
alls = [m for s in ("nonlands", "lands") for m, d, n in rows[s] for _ in range(copies(d))]
shape = (f"10: {sum(x==10 for x in alls)} / 8-9: {sum(8<=x<=9 for x in alls)} / 5-7: {sum(5<=x<=7 for x in alls)}"
         f" / 4 or below: {sum(x<=4 for x in alls)}, mean {sum(alls)/max(len(alls), 1):.1f} (by card copy).")
print(f"# {title}: fit scores\n\n## Nonlands\n{table('nonlands')}\n\n## Lands\n{table('lands')}\n\n## Recommended adds\n{table('adds')}\n\n## Shape\n{shape}\n")
with open(f"{raw}/{slug}-flagged.md", "w") as f:
    f.write(f"# {slug}: cards with spread >= 3\n\n" + "".join(f"## {d}\nScores A/B/C: {sc}\n- A: {n[0]}\n- B: {n[1]}\n- C: {n[2]}\n\n" for d, sc, n in flagged))
print(f"{slug}: {shape} {len(flagged)} flagged", file=sys.stderr)
