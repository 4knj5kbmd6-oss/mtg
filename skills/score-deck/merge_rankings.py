"""Merge the rankers' judgments into rankings.md, computing every cell a ranker does not judge.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score-deck/merge_rankings.py [--recompute] <run_dir>
The decks are the slugs of <run_dir>/*-counts.md. Each <run_dir>/rankings-<letter>.md, in the ranker agent's shape,
must hold each deck exactly once, each JUDGED criterion a whole number from 1 to 9 and its Bracket 1 to 5, optionally
followed by ", top" or ", low"; anything else exits 1 with one "rankings-<letter>.md: <slug>: <what>" line per fault
and writes nothing. Writes <run_dir>/rankings.md: its Rankings, Criteria, Speed, Card quality and Ledger tables, where
- each JUDGED criterion is the median x of the rankers' values, the mean of the middle two when their count is even,
  mapped onto 1 to 10 as 1 + (x - 1) * 9 / 8;
- Speed is the mean of the mapped JUDGED axes; the Criteria table shows SCORED and the Speed table the JUDGED axes,
  every criterion and axis on 1 to 10, their decks in the same order and numbering;
- each COMPUTED criterion is read from the deck's counts file: Interaction the level below, its Ledger row's Count
  "<a> answers, <i> instant, <w> weighted", its Cards the Answers row's Cards; Card quality the mean of the Counts of
  the QUALITY rows, its Ledger row's Count "cmdr salt <a>, cmdr price <b>, 99 salt <c>, 99 price <d>", its Cards the
  cards those rows name, and the Card quality table those four levels and USD, the dollar sums of the Commander price
  and 99 price rows added;
- the Score is the mean over SCORED of (value as written - 1) / 9 * 100; every mapped axis, mean and Score is an exact
  fraction rounded half up to one decimal, USD half up to a whole dollar;
- each ranker's own Score, computed the same way from its own values, picks the median ranker (the lower middle when
  even), whose Bracket, Why and Ledger rows the deck takes;
- the Bracket is 5 when the deck's plan.md carries `- **cEDH:** yes`, whatever the rankers wrote, and a 5 of any other
  deck is "4, top";
- Commander is the front-face names of list.txt's commander lines, joined by " / ", linked to output/decks/<slug>/;
  Colours the commanders' colour identity from oracle.json in WUBRG order, or C with none; Game Changers facts.py's
  game_changers() joined by ", ", or none; the link [Moxfield](https://moxfield.com/decks/<id>) with the id from
  moxfield.json's decks, or - when it lacks the deck;
- rows sort by Score descending, then by the deck's mean place across the rankers' tables, then by slug.
Prints to stderr, per deck, the JUDGED criteria the rankers put SPLIT or more apart, each with its values in letter
order, and per deck whose Bracket the plan changed "<slug>: bracket 5 by plan" or "<slug>: bracket 5 capped at 4,
top". With --recompute, rankings.md beside output/ and the counts files are the only sources and no ranker file is
read: each deck's JUDGED axes in its Speed table as written, its Bracket, Why and JUDGED Ledger rows, and its row
there as its place; a deck of the run it lacks exits 1 with "<slug>: not in rankings.md, rank the decks", a file
without a Speed table exits 1 with "rankings.md has no Speed table, rank the decks", and one without a JUDGED column
exits 1 with "rankings.md has no <column> column, rank the decks".

Interaction, what the deck stops. An answer stops an opponent: removal, counter, wipe, redirect, stax or hate piece.
Answers is the counts file's Answers row and instant its Instant-speed answers row; the counts are final. The weighted
count is answers plus instant, so an instant-speed answer counts twice, and the level is 1 + 9 * weighted / 40 rounded
half up, held from 1 to 10: 0 weighted is 1, 40 or more 10."""
import json, math, re, sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import cedh, decklist, named
from tables import split, cells, table
import facts

JUDGED = ("Win", "Development")  # read from the ranker files, judged 1 to 9; Speed is the mean of their mapped medians
QUALITY = ("Commander salt", "Commander price", "99 salt", "99 price")  # Card quality is the mean of these levels
COMPUTED = ("Interaction", "Card quality")  # read from the counts files
SCORED = ("Speed",) + COMPUTED  # the Score's criteria, each 1 to 10
ANSWERED = ("Answers", "Instant-speed answers")
COUNTED = ANSWERED + QUALITY  # the counts file's rows read
SPLIT = 4  # a criterion the rankers put this far apart is printed
JUDGMENTS = "| Deck | " + " | ".join(JUDGED) + " | Bracket | Why |"
RANKINGS = "| # | Commander | Colours | Bracket | Score | Game Changers | Why | |"
CRITERIA = "| # | Commander | " + " | ".join(SCORED) + " |"
SPEED = "| # | Commander | " + " | ".join(JUDGED) + " |"
CARD_QUALITY = "| # | Commander | " + " | ".join(QUALITY) + " | USD |"
LEDGER = "| Commander | Criterion | Value | Count | Cards |"
BRACKET = re.compile(r"[1-5](, (top|low))?")
DOLLARS = re.compile(r"\$(\d+(?:\.\d+)?)")
MOXFIELD, RANKED = Path("moxfield.json"), Path("rankings.md")

def tenths(x):
    """x rounded half up to one decimal, exactly"""
    return Fraction(math.floor(x * 10 + Fraction(1, 2)), 10)

def shown(x): return f"{float(x):.1f}"

def mean(values): return Fraction(sum(values), len(values))

def middle(values):
    """the median of values, the mean of the middle two when their count is even, exactly"""
    v, n = sorted(values), len(values)
    return mean(v[(n - 1) // 2:n // 2 + 1])

def axis(x):
    """a JUDGED value x, judged 1 to 9, mapped onto 1 to 10, to one decimal"""
    return tenths(1 + (x - 1) * Fraction(9, 8))

def score(criteria):
    """the Score of the SCORED criteria: the mean of each normalised from 1 to 10, out of 100, to one decimal"""
    return tenths(mean([(v - 1) / Fraction(9) for v in criteria]) * 100)

def scored(values, levels):
    """the SCORED criteria of mapped JUDGED values and the COMPUTED levels, Speed the mean of the values to one
    decimal"""
    return [tenths(mean(values))] + list(levels)

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
    """(level, Ledger Count) of Interaction on {category: Count} of a counts file"""
    a, i = counts["Answers"], counts["Instant-speed answers"]
    w = a + i
    level = min(10, math.floor(1 + Fraction(9 * w, 40) + Fraction(1, 2)))
    return level, f"{a} answers, {i} instant, {w} weighted"

def card_quality(got):
    """(level, Ledger row past the deck's name, the Card quality table's cells past it) of Card quality from a counts
    file's rows {category: (Count, Cards)}"""
    levels = [int(got[r][0]) for r in QUALITY]
    level = tenths(mean(levels))
    cards = "; ".join(c for r in QUALITY for c in got[r][1].split("; ")[1:] if c != "-") or "-"
    usd = sum(Fraction(DOLLARS.search(got[r][1])[1]) for r in ("Commander price", "99 price"))
    count = "cmdr salt {}, cmdr price {}, 99 salt {}, 99 price {}".format(*levels)
    return level, ["Card quality", shown(level), count, cards], [*map(shown, levels), str(math.floor(usd + Fraction(1, 2)))]

def computed(got):
    """({criterion: (level, its Ledger row past the deck's name)} of each COMPUTED criterion, the Card quality table's
    cells past the deck's name) from a counts file's rows {category: (Count, Cards)}"""
    level, count = interaction({c: int(got[c][0]) for c in ANSWERED})
    quality, ledger, table_cells = card_quality(got)
    return {"Interaction": (level, ["Interaction", str(level), count, got["Answers"][1]]),
            "Card quality": (quality, ledger)}, table_cells

def merged(run, decks, comp):
    """({slug: (mean place, [mapped JUDGED values], bracket, why, Ledger rows)}, faults) from the ranker files and
    each deck's computed criteria; prints the split criteria"""
    files = sorted(run.glob("rankings-?.md"))
    if not files: sys.exit(f"no ranker files {run}/rankings-<letter>.md")
    rankers, ledgers, faults = zip(*(judgments(p, decks) for p in files))
    if faults := sum(faults, []): return {}, faults
    found = {}
    for d in decks:
        got, own = [r[d] for r in rankers], [comp[d][c][0] for c in COMPUTED]
        each = list(zip(*(g[1] for g in got)))
        median = sorted(range(len(got)), key=lambda i: score(scored([axis(v) for v in got[i][1]], own)))[
            (len(got) - 1) // 2]
        _, _, bracket, why = got[median]
        found[d] = (mean([g[0] for g in got]), [axis(middle(v)) for v in each], bracket, why,
                    sorted(ledgers[median].get(d, []), key=lambda r: JUDGED.index(r[0])))
        apart = [f"{n} {'/'.join(map(str, v))}" for n, v in zip(JUDGED, each) if max(v) - min(v) >= SPLIT]
        if apart: print(f"{d}: split {', '.join(apart)}", file=sys.stderr)
    return found, []

def by_plan(judged):
    """judged with each deck's bracket 5 when its plan declares cEDH and a 5 otherwise capped at "4, top"; prints a
    line per deck changed"""
    out = {}
    for d, (place, values, bracket, why, ledger) in judged.items():
        held = "5" if cedh(d) else "4, top" if bracket.startswith("5") else bracket
        if held != bracket: print(f"{d}: bracket 5 {'by plan' if held == '5' else 'capped at 4, top'}", file=sys.stderr)
        out[d] = (place, values, held, why, ledger)
    return out

def numbered(lines):
    """(the columns, {#: {column: cell}}) of the "| # |" table in lines"""
    head = next((l for l in lines if l.startswith("| # |")), "")
    columns = [c.strip() for c in head.strip().strip("|").split("|")]
    return columns, {r[0]: dict(zip(columns, r)) for r in cells(lines)}

def written(decks):
    """({slug: (place, [mapped JUDGED values], bracket, why, Ledger rows)}, faults) as rankings.md holds them"""
    secs = dict(split(RANKED.read_text())) if RANKED.exists() else {None: []}
    if RANKED.exists() and "## Speed" not in secs: return {}, ["rankings.md has no Speed table, rank the decks"]
    heads, speed = numbered(secs.get("## Speed", []))
    if missing := [c for c in JUDGED if RANKED.exists() and c not in heads]:
        return {}, [f"rankings.md has no {c} column, rank the decks" for c in missing]
    found, owners, seen = {}, {}, Counter()
    for place, r in enumerate(cells(secs[None])):
        name, d = re.fullmatch(r"\[(.*)\]\(output/decks/([^/)]+)/?\)", r[1]).groups()
        found[d] = (place, [Fraction(speed[r[0]][c]) for c in JUDGED], r[3], r[6], [])
        owners.setdefault(name, []).append(d)
    for r in rows(secs.get("## Ledger", []), "Commander"):  # the k-th row of a name and criterion is its k-th deck's
        k, seen[r[0], r[1]] = seen[r[0], r[1]], seen[r[0], r[1]] + 1
        if r[1] in JUDGED and k < len(owners.get(r[0], [])): found[owners[r[0]][k]][4].append(r[1:])
    faults = [f"{d}: not in rankings.md, rank the decks" for d in decks if d not in found]
    return {d: found[d] for d in decks if d in found}, faults

def write(run, judged, comp, quality):
    """write <run>/rankings.md from {slug: (place, [mapped JUDGED values], bracket, why, Ledger rows)}, each deck's
    computed criteria and its Card quality table cells, every other cell computed"""
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
        decks.append((-score(criteria), place, d, row, [name] + [shown(v) for v in criteria],
                      [name] + [shown(v) for v in values], [name] + quality[d],
                      [[name] + r for r in ledger + [comp[d][c][1] for c in COMPUTED]]))
    decks.sort(key=lambda r: r[:3])
    Path(run, "rankings.md").write_text(
        "# Rankings\n\n" + table(RANKINGS, [[str(i)] + r[3] for i, r in enumerate(decks, 1)])
        + "\n\n## Criteria\n\n" + table(CRITERIA, [[str(i)] + r[4] for i, r in enumerate(decks, 1)])
        + "\n\n## Speed\n\n" + table(SPEED, [[str(i)] + r[5] for i, r in enumerate(decks, 1)])
        + "\n\n## Card quality\n\n" + table(CARD_QUALITY, [[str(i)] + r[6] for i, r in enumerate(decks, 1)])
        + "\n\n## Ledger\n\n" + table(LEDGER, [l for r in decks for l in r[7]]) + "\n")

def facts_of(run):
    """(the run's decks, {slug: computed criteria}, {slug: Card quality table cells}) from <run>/*-counts.md; exits
    naming a counts file that lacks a row"""
    decks = sorted(p.name.removesuffix("-counts.md") for p in run.glob("*-counts.md"))
    if not decks: sys.exit(f"no fact files {run}/<slug>-counts.md, run facts.py")
    got = {d: {r[0]: r[1:] for r in cells(Path(run, f"{d}-counts.md").read_text().splitlines())} for d in decks}
    if faults := [f"{d}-counts.md: no {c} row, rerun facts.py" for d in decks for c in COUNTED if c not in got[d]]:
        sys.exit("\n".join(faults))
    both = {d: computed(got[d]) for d in decks}
    return decks, {d: c for d, (c, _) in both.items()}, {d: q for d, (_, q) in both.items()}

def main():
    args = sys.argv[1:]
    recompute = args[:1] == ["--recompute"]
    if len(args) != 1 + recompute: sys.exit(__doc__)
    run = Path(args[-1])
    decks, comp, quality = facts_of(run)
    judged, faults = written(decks) if recompute else merged(run, decks, comp)
    if faults: sys.exit("\n".join(faults))
    write(run, by_plan(judged), comp, quality)

if __name__ == "__main__": main()
