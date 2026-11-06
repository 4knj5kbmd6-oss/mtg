"""Merge the rankers' judgments into rankings.md, computing every cell a ranker does not judge.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/merge_rankings.py <run_dir>
The decks are the slugs of <run_dir>/*-counts.md. Each <run_dir>/rankings-<letter>.md, in the ranker agent's shape,
must hold each deck exactly once, its JUDGED criteria whole numbers from 1 to 9, its Kill turn N or N-M and its Bracket
1 to 5, optionally followed by ", top" or ", low"; anything else exits 1 with one "rankings-<letter>.md: <slug>: <what>"
line per fault and writes nothing. Writes <run_dir>/rankings.md: its Rankings, Criteria and Ledger tables, where
- each JUDGED criterion is the mean of the rankers' values sorted with the lowest and highest dropped while five or more
  remain (the middle three of five, all of four or fewer);
- each COMPUTED criterion is the Count of the counts file's row of that name, its Cards the Ledger row's Count (up to
  the first "; ") and Cards;
- the Score is (mean of the criteria as written - 1) / 8 * 100; every mean and Score is an exact fraction rounded half
  up to one decimal;
- each ranker's own Score, computed the same way from its own values, picks the median ranker (the lower middle when
  even), whose Bracket, Kill turn, Why and Ledger rows the deck takes;
- Commander is the front-face names of list.txt's commander lines, joined by " / ", linked to output/decks/<slug>/;
  Colours the commanders' colour identity from oracle.json in WUBRG order, or C with none; Game Changers facts.py's
  game_changers() joined by ", ", or none; the link [Moxfield](https://moxfield.com/decks/<id>) with the id from
  moxfield.json's decks, or - when it lacks the deck;
- rows sort by Score descending, then by the deck's mean place across the rankers' tables, then by slug.
Prints to stderr, per deck, the JUDGED criteria the rankers put SPLIT or more apart, each with its values in letter
order."""
import json, math, re, sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import decklist, named
from tables import split, cells, table
import facts

JUDGED = ("Speed", "Resilience", "Interaction")  # read from the ranker files
COMPUTED = ("Salt",)  # read from the counts files
SPLIT = 4  # a criterion the rankers put this far apart is printed
JUDGMENTS = "| Deck | " + " | ".join(JUDGED) + " | Kill turn | Bracket | Why |"
RANKINGS = "| # | Commander | Colours | Bracket | Score | Kill turn | Game Changers | Why | |"
CRITERIA = "| # | Commander | " + " | ".join(JUDGED + COMPUTED) + " |"
LEDGER = "| Commander | Criterion | Value | Count | Cards |"
KILL, BRACKET = re.compile(r"\d+(-\d+)?"), re.compile(r"[1-5](, (top|low))?")
MOXFIELD = Path("moxfield.json")

def tenths(x):
    """x rounded half up to one decimal, exactly"""
    return Fraction(math.floor(x * 10 + Fraction(1, 2)), 10)

def shown(x): return f"{float(x):.1f}"

def mean(values): return Fraction(sum(values), len(values))

def middle(values):
    """the mean of values sorted, the lowest and highest dropped while five or more remain, to one decimal"""
    v = sorted(values)
    while len(v) >= 5: v = v[1:-1]
    return tenths(mean(v))

def score(values): return tenths((mean(values) - 1) / 8 * 100)

def rows(lines, head):
    """the data rows of lines' table, as lists of cells, its header row left out"""
    return [r for r in cells(lines) if r[0] != head]

def judgments(path, decks):
    """({slug: (place, [JUDGED values], bracket, kill, why)}, {slug: Ledger rows}, faults) of one ranker file"""
    secs = dict(split(path.read_text()))
    got = rows(secs[None], "Deck")
    width = JUDGMENTS.count("|") - 1
    seen = Counter(r[0] for r in got)
    faults = [f"{d}: missing" for d in decks if d not in seen]
    faults += [f"{d}: not a deck of the run" for d in seen if d not in decks]
    faults += [f"{d}: listed {n} times" for d, n in seen.items() if n > 1 and d in decks]
    out = {}
    for place, r in enumerate(got):
        if len(r) != width:
            faults.append(f"{r[0]}: {len(r)} cells, not {width}"); continue
        values, (kill, bracket, why) = r[1:1 + len(JUDGED)], r[1 + len(JUDGED):]
        faults += [f"{r[0]}: {n} {v} is not a whole number from 1 to 9" for n, v in zip(JUDGED, values)
                   if not re.fullmatch(r"[1-9]", v)]
        if not KILL.fullmatch(kill): faults.append(f"{r[0]}: Kill turn {kill} is not N or N-M")
        if not BRACKET.fullmatch(bracket): faults.append(f"{r[0]}: Bracket {bracket} is not 1 to 5 with ', top' or ', low'")
        out[r[0]] = (place, [int(v) if v.isdigit() else 0 for v in values], bracket, kill, why)
    ledger = {}
    for r in rows(secs.get("## Ledger", []), "Deck"):
        if r[1:2] and r[1] in JUDGED: ledger.setdefault(r[0], []).append(r[1:])
    return out, ledger, [f"{path.name}: {f}" for f in faults]

def computed(run, slug):
    """{criterion: (level, its Ledger row past the deck's name)} of each COMPUTED criterion the deck's counts file has a
    row for"""
    got = {r[0]: r for r in cells(Path(run, f"{slug}-counts.md").read_text().splitlines())}
    return {c: (int(got[c][1]), [c, got[c][1], count, cards or "-"])
            for c in COMPUTED if c in got for count, _, cards in [got[c][2].partition("; ")]}

def merged(rankers, comp):
    """{slug: (mean place, [JUDGED values], bracket, kill, why, Ledger rows)} from each ranker's (judgments, Ledger)
    and each deck's computed(); prints the split criteria"""
    found = {}
    for d in comp:
        got, own = [r[d] for r, _ in rankers], [comp[d][c][0] for c in COMPUTED]
        each = list(zip(*(g[1] for g in got)))
        median = sorted(range(len(got)), key=lambda i: score(got[i][1] + own))[(len(got) - 1) // 2]
        _, _, bracket, kill, why = got[median]
        found[d] = (mean([g[0] for g in got]), [middle(v) for v in each], bracket, kill, why,
                    sorted(rankers[median][1].get(d, []), key=lambda r: JUDGED.index(r[0])))
        apart = [f"{n} {'/'.join(map(str, v))}" for n, v in zip(JUDGED, each) if max(v) - min(v) >= SPLIT]
        if apart: print(f"{d}: split {', '.join(apart)}", file=sys.stderr)
    return found

def write(run, judged, comp):
    """write <run>/rankings.md from {slug: (place, [JUDGED values], bracket, kill, why, Ledger rows)} and each deck's
    computed(), every other cell computed"""
    oracle = named()
    ids = {slug: i for i, slug in json.loads(MOXFIELD.read_text()).get("decks", {}).items()} if MOXFIELD.exists() else {}
    decks = []
    for d, (place, values, bracket, kill, why, ledger) in judged.items():
        criteria = values + [Fraction(comp[d][c][0]) for c in COMPUTED]
        commanders = [n for _, n in decklist(d)[0]]
        name = " / ".join(n.split(" // ")[0] for n in commanders)
        colours = {c for n in commanders for c in (oracle.get(n.casefold()) or {}).get("color_identity", [])}
        link = f"[Moxfield](https://moxfield.com/decks/{ids[d]})" if d in ids else "-"
        row = [f"[{name}](output/decks/{d}/)", "".join(c for c in "WUBRG" if c in colours) or "C", bracket,
               shown(score(criteria)), kill, ", ".join(facts.game_changers(d)) or "none", why, link]
        decks.append((-score(criteria), place, d, row, [name] + [shown(v) for v in criteria],
                      [[name] + r for r in ledger + [comp[d][c][1] for c in COMPUTED]]))
    decks.sort(key=lambda r: r[:3])
    Path(run, "rankings.md").write_text(
        "# Rankings\n\n" + table(RANKINGS, [[str(i)] + r[3] for i, r in enumerate(decks, 1)])
        + "\n\n## Criteria\n\n" + table(CRITERIA, [[str(i)] + r[4] for i, r in enumerate(decks, 1)])
        + "\n\n## Ledger\n\n" + table(LEDGER, [l for r in decks for l in r[5]]) + "\n")

def facts_of(run):
    """(the run's decks, {slug: computed()}, faults) from <run>/*-counts.md"""
    decks = sorted(p.name.removesuffix("-counts.md") for p in run.glob("*-counts.md"))
    if not decks: sys.exit(f"no fact files {run}/<slug>-counts.md, run facts.py")
    comp = {d: computed(run, d) for d in decks}
    return decks, comp, [f"{d}-counts.md: no {c} row, rerun facts.py" for d in decks for c in COMPUTED if c not in comp[d]]

def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    run = Path(sys.argv[1])
    decks, comp, faults = facts_of(run)
    files = sorted(run.glob("rankings-?.md"))
    if not files: sys.exit(f"no ranker files {run}/rankings-<letter>.md")
    rankers = [judgments(p, decks) for p in files]
    if faults := faults + [f for _, _, fs in rankers for f in fs]: sys.exit("\n".join(faults))
    write(run, merged([r[:2] for r in rankers], comp), comp)

if __name__ == "__main__": main()
