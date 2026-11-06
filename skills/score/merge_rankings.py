"""Merge the rankers' judgments into rankings.md, computing every cell a ranker does not judge.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/merge_rankings.py [--recompute] <run_dir>
The decks are the slugs of <run_dir>/*-counts.md. Each <run_dir>/rankings-<letter>.md, in the ranker agent's shape,
must hold each deck exactly once, its JUDGED criteria whole numbers from 1 to 9 and its Bracket 1 to 5, optionally
followed by ", top" or ", low"; anything else exits 1 with one "rankings-<letter>.md: <slug>: <what>" line per fault
and writes nothing. Writes <run_dir>/rankings.md: its Rankings, Criteria and Ledger tables, where
- each JUDGED criterion is the mean of the rankers' values sorted with the lowest and highest dropped while five or more
  remain (the middle three of five, all of four or fewer);
- Resilience is the mean of the merged AXES; the Criteria table shows SCORED, then the AXES;
- each COMPUTED criterion is read from the deck's counts file: Salt the Count of its Salt row, its Cards the Ledger
  row's Count (up to the first "; ") and Cards; Interaction the level of the Interaction table below, its Ledger row's
  Count "<n> answers, <m> instant; <counters>/<creature>/<noncreature>", each coverage yes or no, its Cards the
  Answers row's Cards;
- the Score is (mean of SCORED as written - 1) / 8 * 100; every mean and Score is an exact fraction rounded half
  up to one decimal;
- each ranker's own Score, computed the same way from its own values, picks the median ranker (the lower middle when
  even), whose Bracket, Why and Ledger rows the deck takes;
- Commander is the front-face names of list.txt's commander lines, joined by " / ", linked to output/decks/<slug>/;
  Colours the commanders' colour identity from oracle.json in WUBRG order, or C with none; Game Changers facts.py's
  game_changers() joined by ", ", or none; the link [Moxfield](https://moxfield.com/decks/<id>) with the id from
  moxfield.json's decks, or - when it lacks the deck;
- rows sort by Score descending, then by the deck's mean place across the rankers' tables, then by slug.
Prints to stderr, per deck, the JUDGED criteria the rankers put SPLIT or more apart, each with its values in letter
order. With --recompute, rankings.md beside output/ is the only judged source and no ranker file is read: each deck's
JUDGED criteria as written, its Bracket, Why and JUDGED Ledger rows, and its row there as its place; a deck of the
run it lacks exits 1 with "<slug>: not in rankings.md, rank the decks", and a Criteria table without a JUDGED column
exits 1 with "rankings.md has no <criterion> column, rank the decks".

Interaction, what the deck stops. An answer stops an opponent: removal, counter, wipe, redirect, stax or hate piece.
Answers is the counts file's Answers row, instant its Instant-speed answers row, a wipe its Wipes row above 0, and the
three coverages its Counters, Creature removal and Noncreature removal rows above 0; the counts are final. The level is
the highest row the deck meets:
| 9 | 15+ answers, 10+ instant, all three of counters, creature removal and noncreature removal present |
| 7 | 11+ answers, 7+ instant, creature and noncreature removal present, a wipe |
| 5 | 7+ answers, or 11+ answers with fewer than half instant or one of the three coverages missing |
| 3 | 3+ answers |
| 1 | 0-2 answers |"""
import json, math, re, sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import decklist, named
from tables import split, cells, table
import facts

AXES = ("Setup", "Rebuild", "Flow")  # Resilience is their mean
JUDGED = ("Speed",) + AXES  # read from the ranker files
COMPUTED = ("Interaction", "Salt")  # read from the counts files, from these rows
SCORED = ("Speed", "Resilience") + COMPUTED  # the Score's criteria
COUNTED = ("Answers", "Instant-speed answers", "Wipes", "Counters", "Creature removal", "Noncreature removal", "Salt")
SPLIT = 4  # a criterion the rankers put this far apart is printed
JUDGMENTS = "| Deck | " + " | ".join(JUDGED) + " | Bracket | Why |"
RANKINGS = "| # | Commander | Colours | Bracket | Score | Game Changers | Why | |"
CRITERIA = "| # | Commander | " + " | ".join(SCORED + AXES) + " |"
LEDGER = "| Commander | Criterion | Value | Count | Cards |"
BRACKET = re.compile(r"[1-5](, (top|low))?")
MOXFIELD, RANKED = Path("moxfield.json"), Path("rankings.md")

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

def scored(values, levels):
    """the SCORED criteria of JUDGED values and the COMPUTED levels, Resilience the mean of the AXES to one decimal"""
    return [values[0], tenths(mean(values[1:]))] + list(levels)

def rows(lines, head):
    """the data rows of lines' table, as lists of cells, its header row left out"""
    return [r for r in cells(lines) if r[0] != head]

def judgments(path, decks):
    """({slug: (place, [JUDGED values], bracket, why)}, {slug: Ledger rows}, faults) of one ranker file"""
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
        values, (bracket, why) = r[1:1 + len(JUDGED)], r[1 + len(JUDGED):]
        faults += [f"{r[0]}: {n} {v} is not a whole number from 1 to 9" for n, v in zip(JUDGED, values)
                   if not re.fullmatch(r"[1-9]", v)]
        if not BRACKET.fullmatch(bracket): faults.append(f"{r[0]}: Bracket {bracket} is not 1 to 5 with ', top' or ', low'")
        out[r[0]] = (place, [int(v) if v.isdigit() else 0 for v in values], bracket, why)
    ledger = {}
    for r in rows(secs.get("## Ledger", []), "Deck"):
        if r[1:2] and r[1] in JUDGED: ledger.setdefault(r[0], []).append(r[1:])
    return out, ledger, [f"{path.name}: {f}" for f in faults]

def interaction(counts):
    """(level, Ledger Count) of the Interaction table on {category: Count} of a counts file"""
    a, i, wipe = counts["Answers"], counts["Instant-speed answers"], counts["Wipes"] > 0
    cover = [counts[c] > 0 for c in ("Counters", "Creature removal", "Noncreature removal")]
    level = next(l for l, met in [(9, a >= 15 and i >= 10 and all(cover)),
                                  (7, a >= 11 and i >= 7 and all(cover[1:]) and wipe),
                                  (5, a >= 7), (3, a >= 3), (1, True)] if met)
    return level, f"{a} answers, {i} instant; " + "/".join("yes" if c else "no" for c in cover)

def computed(got):
    """{criterion: (level, its Ledger row past the deck's name)} of each COMPUTED criterion from a counts file's rows
    {category: (Count, Cards)}"""
    level, count = interaction({c: int(got[c][0]) for c in COUNTED})
    salt, _, salty = got["Salt"][1].partition("; ")
    return {"Interaction": (level, ["Interaction", str(level), count, got["Answers"][1]]),
            "Salt": (int(got["Salt"][0]), ["Salt", got["Salt"][0], salt, salty or "-"])}

def merged(run, decks, comp):
    """({slug: (mean place, [JUDGED values], bracket, why, Ledger rows)}, faults) from the ranker files and each
    deck's computed(); prints the split criteria"""
    files = sorted(run.glob("rankings-?.md"))
    if not files: sys.exit(f"no ranker files {run}/rankings-<letter>.md")
    rankers, ledgers, faults = zip(*(judgments(p, decks) for p in files))
    if faults := sum(faults, []): return {}, faults
    found = {}
    for d in decks:
        got, own = [r[d] for r in rankers], [comp[d][c][0] for c in COMPUTED]
        each = list(zip(*(g[1] for g in got)))
        median = sorted(range(len(got)), key=lambda i: score(scored(got[i][1], own)))[(len(got) - 1) // 2]
        _, _, bracket, why = got[median]
        found[d] = (mean([g[0] for g in got]), [middle(v) for v in each], bracket, why,
                    sorted(ledgers[median].get(d, []), key=lambda r: JUDGED.index(r[0])))
        apart = [f"{n} {'/'.join(map(str, v))}" for n, v in zip(JUDGED, each) if max(v) - min(v) >= SPLIT]
        if apart: print(f"{d}: split {', '.join(apart)}", file=sys.stderr)
    return found, []

def written(decks):
    """({slug: (place, [JUDGED values], bracket, why, Ledger rows)}, faults) as rankings.md holds them"""
    secs = dict(split(RANKED.read_text())) if RANKED.exists() else {None: []}
    head = next((l for l in secs.get("## Criteria", []) if l.startswith("| # |")), "")
    columns = [c.strip() for c in head.strip().strip("|").split("|")]
    if missing := [c for c in JUDGED if RANKED.exists() and c not in columns]:
        return {}, [f"rankings.md has no {c} column, rank the decks" for c in missing]
    crit = {r[0]: r for r in cells(secs.get("## Criteria", []))}
    found, owners, seen = {}, {}, Counter()
    for place, r in enumerate(cells(secs[None])):
        name, d = re.fullmatch(r"\[(.*)\]\(output/decks/([^/)]+)/?\)", r[1]).groups()
        found[d] = (place, [Fraction(crit[r[0]][columns.index(c)]) for c in JUDGED], r[3], r[6], [])
        owners.setdefault(name, []).append(d)
    for r in rows(secs.get("## Ledger", []), "Commander"):  # the k-th row of a name and criterion is its k-th deck's
        k, seen[r[0], r[1]] = seen[r[0], r[1]], seen[r[0], r[1]] + 1
        if r[1] in JUDGED and k < len(owners.get(r[0], [])): found[owners[r[0]][k]][4].append(r[1:])
    faults = [f"{d}: not in rankings.md, rank the decks" for d in decks if d not in found]
    return {d: found[d] for d in decks if d in found}, faults

def write(run, judged, comp):
    """write <run>/rankings.md from {slug: (place, [JUDGED values], bracket, why, Ledger rows)} and each deck's
    computed(), every other cell computed"""
    oracle = named()
    ids = {slug: i for i, slug in json.loads(MOXFIELD.read_text()).get("decks", {}).items()} if MOXFIELD.exists() else {}
    decks = []
    for d, (place, values, bracket, why, ledger) in judged.items():
        criteria = scored(values, [Fraction(comp[d][c][0]) for c in COMPUTED])
        commanders = [n for _, n in decklist(d)[0]]
        name = " / ".join(n.split(" // ")[0] for n in commanders)
        colours = {c for n in commanders for c in (oracle.get(n.casefold()) or {}).get("color_identity", [])}
        link = f"[Moxfield](https://moxfield.com/decks/{ids[d]})" if d in ids else "-"
        row = [f"[{name}](output/decks/{d}/)", "".join(c for c in "WUBRG" if c in colours) or "C", bracket,
               shown(score(criteria)), ", ".join(facts.game_changers(d)) or "none", why, link]
        decks.append((-score(criteria), place, d, row, [name] + [shown(v) for v in criteria + values[1:]],
                      [[name] + r for r in ledger + [comp[d][c][1] for c in COMPUTED]]))
    decks.sort(key=lambda r: r[:3])
    Path(run, "rankings.md").write_text(
        "# Rankings\n\n" + table(RANKINGS, [[str(i)] + r[3] for i, r in enumerate(decks, 1)])
        + "\n\n## Criteria\n\n" + table(CRITERIA, [[str(i)] + r[4] for i, r in enumerate(decks, 1)])
        + "\n\n## Ledger\n\n" + table(LEDGER, [l for r in decks for l in r[5]]) + "\n")

def facts_of(run):
    """(the run's decks, {slug: computed()}) from <run>/*-counts.md; exits naming a counts file that lacks a row"""
    decks = sorted(p.name.removesuffix("-counts.md") for p in run.glob("*-counts.md"))
    if not decks: sys.exit(f"no fact files {run}/<slug>-counts.md, run facts.py")
    got = {d: {r[0]: r[1:] for r in cells(Path(run, f"{d}-counts.md").read_text().splitlines())} for d in decks}
    if faults := [f"{d}-counts.md: no {c} row, rerun facts.py" for d in decks for c in COUNTED if c not in got[d]]:
        sys.exit("\n".join(faults))
    return decks, {d: computed(got[d]) for d in decks}

def main():
    args = sys.argv[1:]
    recompute = args[:1] == ["--recompute"]
    if len(args) != 1 + recompute: sys.exit(__doc__)
    run = Path(args[-1])
    decks, comp = facts_of(run)
    judged, faults = written(decks) if recompute else merged(run, decks, comp)
    if faults: sys.exit("\n".join(faults))
    write(run, judged, comp)

if __name__ == "__main__": main()
