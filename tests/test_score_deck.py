import json
from urllib.error import HTTPError
from pathlib import Path
import pytest
from conftest import run, read
import facts, fetch_brackets, fetch_syntax, merge_rankings, tables


# each deck's Win and Development from rankers A to E; zara's Card quality is 5.3, kor's 2.8, and both decks'
# Interaction 1, their cards untagged
JUDGED = {"zara": {"A": [6, 5], "B": [7, 6], "C": [3, 4]},
          "kor": {"A": [5, 6], "B": [8, 7], "C": [8, 7]}}
OWN = dict(zip("ABCDE", ["3", "4", "2", "3, top", "3"]))  # each ranker's Bracket
UNTAGGED = "1 | 0 answers, 0 instant, 0 weighted | -"  # an untagged deck's Interaction Ledger cells past the criterion
# zara's commander salt 0.525 is level 4 and its 10 dollars 6; its 99's salt mean 3.0 / 4 = 0.75 is 8 and its 200
# dollars 3: Card quality 21 / 4 = 5.25, 5.3, USD 210. kor's 0.45 is 3 and its 1 dollar 1; its 99's salt 0.6 is 6 and
# its 4.25 dollars 1: Card quality 11 / 4 = 2.75, 2.8, USD 5
SALTS = {"Zara, Tide Caller": 0.525, "Kor Skyfisher": 0.45, "Sol Ring": 0.6, "Brine Elemental": 2.4,
         "Coral Signet": 0.0, "Kelp Weaver": 0.0, "Island": 0.05}
PRICES = {"Zara, Tide Caller": 10.0, "Kor Skyfisher": 1.0, "Sol Ring": 2.0, "Brine Elemental": 197.0, "Island": 0.25}


def flat(speed):
    """a ranker's JUDGED values with both Speed axes at speed"""
    return [speed] * 2


def decks(salts=SALTS, prices=PRICES):
    """the fixture with a second deck, kor, the commanders given colours and the cards these salts and prices,
    moxfield.json naming both, and run/ holding both decks' counts files"""
    oracle = json.loads(read("output/data/oracle.json"))
    oracle["cards"]["Kor Skyfisher"] = {"name": "Kor Skyfisher", "type_line": "Creature — Kor Bird Soldier",
                                        "color_identity": ["W"]}
    oracle["cards"]["Zara, Tide Caller"]["color_identity"] = ["U"]
    for field, values in (("salt", salts), ("price", prices)):
        for name, value in values.items(): oracle["cards"][name][field] = value
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    Path("output/decks/kor").mkdir()
    Path("output/decks/kor/list.txt").write_text("1 Kor Skyfisher\n\n1 Sol Ring\n9 Island\n")
    Path("moxfield.json").write_text(json.dumps({"user": "owner", "decks": {"z1": "zara", "k1": "kor"}}))
    Path("run").mkdir(exist_ok=True)
    for slug in ("zara", "kor"): facts.counts("run", slug, 0)


def ledger(slug, x):
    """ranker x's Ledger rows for one deck, each naming the ranker"""
    return [f"| {slug} | {a} | 5 | - | cards {x} |" for a in merge_rankings.JUDGED]


def judgments(head=merge_rankings.JUDGMENTS):
    """the Judgments table's header and rule"""
    return f"{head}\n|{'---|' * (head.count('|') - 1)}\n"


def rankers(judged=JUDGED, letters="ABC", order=None):
    """one run/rankings-<letter>.md per letter in the ranker agent's shape, its decks in order[letter] or strongest
    first by its own values; makes the decks first"""
    if not Path("run").exists(): decks()
    for x in letters:
        slugs = (order or {}).get(x) or sorted(judged, key=lambda d: -sum(judged[d][x]))
        rows = "".join(f"| {d} | {' | '.join(map(str, judged[d][x]))} | {OWN[x]} | why {x} |\n"
                       for d in slugs)
        books = "".join(f"{l}\n" for d in slugs for l in ledger(d, x))
        Path(f"run/rankings-{x}.md").write_text(f"# Judgments ({x})\n\n{judgments()}"
                                                f"{rows}\n## Ledger\n\n| Deck | Criterion | Value | Count | Cards |\n"
                                                f"|---|---|---|---|---|\n{books}")


def ranked():
    """run/rankings.md as {slug: {column: cell}}, its Rankings, Criteria, Speed and Card quality columns by name, its
    decks in order"""
    secs = dict(tables.split(read("run/rankings.md")))
    heads = lambda h: [c.strip() or "Moxfield" for c in h.strip("|").split("|")]
    by = lambda head, sec: {r[0]: dict(zip(heads(head), r)) for r in tables.cells(secs[sec])}
    crit, speed, quality = by(merge_rankings.CRITERIA, "## Criteria"), by(merge_rankings.SPEED, "## Speed"), \
        by(merge_rankings.CARD_QUALITY, "## Card quality")
    return {r[1].split("decks/")[1].rstrip("/)"):
            crit[r[0]] | speed[r[0]] | quality[r[0]] | dict(zip(heads(merge_rankings.RANKINGS), r))
            for r in tables.cells(secs[None])}


def merges(*stderr):
    """ranked() after a merge that succeeds printing these lines"""
    out = run("skills/score-deck/merge_rankings.py", "run")
    assert (out.returncode, out.stderr) == (0, "".join(f"{l}\n" for l in stderr))
    return ranked()


def test_merge_rankings_takes_the_median_of_three_rankers_and_computes_the_rest():
    rankers()
    merges("zara: split Win 6/7/3")
    # zara's Win 6/7/3 has median 6, mapped 6.6, and Development 5/6/4 median 5, mapped 5.5, Speed their mean 6.05;
    # with Interaction 1 and Card quality 5.3 its Score is (5.1 / 9 + 0 / 9 + 4.3 / 9) / 3 * 100 = 34.81; its own
    # Scores 34.8 (6.1), 38.9 (7.2) and 26.7 (3.9) make A the median; kor's Win 8 and Development 7, mapped 8.9 and
    # 7.8, Speed 8.4, with Card quality 2.8 (7.4 + 1.8) / 27 * 100 = 34.07, its own 25.6, 34.1 and 34.1 make B the
    # median
    assert read("run/rankings.md") == f"""# Rankings

{merge_rankings.RANKINGS}
|---|---|---|---|---|---|---|---|
| 1 | [Zara, Tide Caller](output/decks/zara/) | U | 3 | 34.8 | none | why A | [Moxfield](https://moxfield.com/decks/z1) |
| 2 | [Kor Skyfisher](output/decks/kor/) | W | 4 | 34.1 | none | why B | [Moxfield](https://moxfield.com/decks/k1) |

## Criteria

| # | Commander | Speed | Interaction | Card quality |
|---|---|---|---|---|
| 1 | Zara, Tide Caller | 6.1 | 1.0 | 5.3 |
| 2 | Kor Skyfisher | 8.4 | 1.0 | 2.8 |

## Speed

| # | Commander | Win | Development |
|---|---|---|---|
| 1 | Zara, Tide Caller | 6.6 | 5.5 |
| 2 | Kor Skyfisher | 8.9 | 7.8 |

## Card quality

| # | Commander | Commander salt | Commander price | 99 salt | 99 price | USD |
|---|---|---|---|---|---|---|
| 1 | Zara, Tide Caller | 4.0 | 6.0 | 8.0 | 3.0 | 210 |
| 2 | Kor Skyfisher | 3.0 | 1.0 | 6.0 | 1.0 | 5 |

## Ledger

{merge_rankings.LEDGER}
|---|---|---|---|---|
| Zara, Tide Caller | Win | 5 | - | cards A |
| Zara, Tide Caller | Development | 5 | - | cards A |
| Zara, Tide Caller | Interaction | {UNTAGGED} |
| Zara, Tide Caller | Card quality | 5.3 | cmdr salt 4, cmdr price 6, 99 salt 8, 99 price 3 | Zara, Tide Caller 0.53; Zara, Tide Caller $10.00; Brine Elemental 2.40; Brine Elemental $197.00 |
| Kor Skyfisher | Win | 5 | - | cards B |
| Kor Skyfisher | Development | 5 | - | cards B |
| Kor Skyfisher | Interaction | {UNTAGGED} |
| Kor Skyfisher | Card quality | 2.8 | cmdr salt 3, cmdr price 1, 99 salt 6, 99 price 1 | Kor Skyfisher 0.45; Kor Skyfisher $1.00 |
"""


@pytest.mark.parametrize("answers, instant, level", [
    (0, 0, 1),
    (2, 0, 1),  # 1 + 9 * 2 / 40 = 1.45
    (2, 1, 2),  # 1 + 9 * 3 / 40 = 1.675
    (10, 5, 4),  # 1 + 9 * 15 / 40 = 4.375
    (14, 5, 5),  # 1 + 9 * 19 / 40 = 5.275
    (15, 5, 6),  # 1 + 9 * 20 / 40 = 5.5, half up
    (30, 7, 9),  # 1 + 9 * 37 / 40 = 9.325
    (30, 8, 10),  # 1 + 9 * 38 / 40 = 9.55
    (25, 15, 10),  # 1 + 9 * 40 / 40
    (40, 30, 10),  # 1 + 9 * 70 / 40 held at 10
])
def test_interaction_is_1_plus_9_times_the_weighted_answers_over_40_half_up_held_from_1_to_10(answers, instant, level):
    assert merge_rankings.interaction({"Answers": answers, "Instant-speed answers": instant}) == \
        (level, f"{answers} answers, {instant} instant, {answers + instant} weighted")


def test_the_merged_ledgers_interaction_row_carries_the_answers_and_their_cards():
    decks()
    oracle = json.loads(read("output/data/oracle.json"))
    tags = {"Tidal Insight": ["counterspell"], "Wave Breaker": ["removal", "removal-creature"],
            "Brine Elemental": ["removal", "sweeper"]}
    for name, t in tags.items(): oracle["cards"][name]["tags"] = t
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    facts.counts("run", "zara", 0)
    rankers()
    assert merges("zara: split Win 6/7/3")["zara"]["Interaction"] == "2.0"  # 1 + 9 * 4 / 40 = 1.9
    assert "| Zara, Tide Caller | Interaction | 2 | 3 answers, 1 instant, 4 weighted | " \
           "Brine Elemental; Tidal Insight; Wave Breaker |\n" in read("run/rankings.md")


@pytest.mark.parametrize("row", ["Instant-speed answers", "99 price"])
def test_merge_rankings_stops_on_a_counts_file_without_a_row_it_reads(row):
    rankers()
    counts = Path("run/zara-counts.md")
    counts.write_text("".join(l for l in counts.read_text().splitlines(True) if not l.startswith(f"| {row} |")))
    out = run("skills/score-deck/merge_rankings.py", "run")
    assert (out.returncode, out.stderr) == (1, f"zara-counts.md: no {row} row, rerun facts.py\n")


@pytest.mark.parametrize("values, median", [([6, 7, 3], "6.0"), ([3, 5, 6, 9], "5.5"), ([9, 5, 9, 7], "8.0"),
                                            ([1, 9, 5, 6, 7], "6.0"), ([5, 6], "5.5")])
def test_each_judged_criterion_is_the_median_the_mean_of_the_middle_two_when_even(values, median):
    assert merge_rankings.shown(merge_rankings.middle(values)) == median


@pytest.mark.parametrize("value, mapped", [(1, "1.0"), (5, "5.5"), (9, "10.0"), (3, "3.3"), (8, "8.9")])
def test_each_judged_axis_maps_from_1_to_9_onto_1_to_10_half_up(value, mapped):
    # 1 + (x - 1) * 9 / 8: 3 is 3.25, half up, and 8 is 8.875
    assert merge_rankings.shown(merge_rankings.axis(value)) == mapped


def test_merge_rankings_takes_the_median_of_four_and_the_median_rankers_cells():
    # each Speed axis 9 5 9 7 sorts to 5 7 9 9, its median 8, mapped 8.9; own Scores 49.3 32.6 49.3 41.1 make D the
    # median
    four = {"zara": {"A": flat(9), "B": flat(5), "C": flat(9), "D": flat(7)}, "kor": {x: flat(5) for x in "ABCD"}}
    rankers(four, "ABCD")
    got = merges("zara: split Win 9/5/9/7, Development 9/5/9/7")["zara"]
    # (7.9 / 9 + 0 / 9 + 4.3 / 9) / 3 * 100 = 45.19
    assert [got[c] for c in ("Speed", "Interaction", "Card quality", "Score", "Bracket", "Why")] == \
        ["8.9", "1.0", "5.3", "45.2", "3, top", "why D"]
    assert "| Zara, Tide Caller | Win | 5 | - | cards D |" in read("run/rankings.md")


def test_merge_rankings_rounds_speed_half_up():
    rankers({"zara": {"A": [6, 5], "B": [6, 5]}, "kor": {x: flat(5) for x in "AB"}}, "AB")
    assert [merges()["zara"][c] for c in ("Win", "Development", "Speed")] == ["6.6", "5.5", "6.1"]  # 12.1 / 2 = 6.05


def test_speed_is_the_mean_of_its_mapped_axes_and_the_score_normalises_each_criterion_from_1_to_10():
    rankers({"zara": {"A": [5, 3], "B": [6, 3]}, "kor": {x: flat(5) for x in "AB"}}, "AB")
    got = merges()["zara"]
    # Win 5.5, mapped 6.0625, and Development 3, mapped 3.25: 6.1 and 3.3, Speed 9.4 / 2 = 4.7; Speed (4.7 - 1) / 9,
    # Interaction 0 / 9 and Card quality (5.3 - 1) / 9: (3.7 + 0 + 4.3) / 27 * 100 = 29.63
    assert [got[c] for c in ("Win", "Development", "Speed", "Interaction", "Card quality", "Score")] == \
        ["6.1", "3.3", "4.7", "1.0", "5.3", "29.6"]


@pytest.mark.parametrize("criteria, got", [([1, 1, 1], "0.0"), ([10, 10, 10], "100.0"), ([5.5, 1, 10], "50.0"),
                                           ([2, 1, 1], "3.7")])  # 1 / 27 * 100 = 3.70
def test_the_score_is_the_mean_of_each_criterion_normalised_from_1_to_10_out_of_100(criteria, got):
    assert merge_rankings.shown(merge_rankings.score([merge_rankings.Fraction(str(v)) for v in criteria])) == got


def test_card_quality_is_the_mean_of_the_four_levels_to_one_decimal():
    # zara's levels 4 6 8 3 and kor's 3 1 6 1, as decks() gives them
    decks()
    _, comp, quality = merge_rankings.facts_of(Path("run"))
    assert [comp[d]["Card quality"][0] for d in ("zara", "kor")] == [merge_rankings.Fraction(53, 10),
                                                                     merge_rankings.Fraction(28, 10)]
    assert quality == {"zara": ["4.0", "6.0", "8.0", "3.0", "210"], "kor": ["3.0", "1.0", "6.0", "1.0", "5"]}


def test_merge_rankings_breaks_a_tie_by_mean_place_then_by_slug():
    same = {"zara": {x: flat(5) for x in "ABC"}, "kor": {x: flat(5) for x in "ABC"}}
    decks({"Zara, Tide Caller": 0.45, "Kor Skyfisher": 0.45}, {})
    rankers(same, order={"A": ["zara", "kor"], "B": ["zara", "kor"], "C": ["kor", "zara"]})
    assert list(merges()) == ["zara", "kor"]
    for x in "ABC": Path(f"run/rankings-{x}.md").unlink()
    rankers(same, "AB", order={"A": ["zara", "kor"], "B": ["kor", "zara"]})
    assert list(merges()) == ["kor", "zara"]


def test_one_ranker_goes_through_the_merge():
    rankers(letters="B")
    got = merges()
    # zara Speed (7.8 + 6.6) / 2 = 7.2, 1 and Card quality 5.3: (6.2 + 0 + 4.3) / 27 * 100 = 38.89; kor
    # (8.9 + 7.8) / 2 = 8.35, 1 and 2.8: (7.4 + 0 + 1.8) / 27 * 100 = 34.07
    assert [(d, got[d]["Score"], got[d]["Speed"], got[d]["Why"]) for d in got] == \
        [("zara", "38.9", "7.2", "why B"), ("kor", "34.1", "8.4", "why B")]


@pytest.mark.parametrize("change, faults", [
    (lambda t: t.replace("| kor |", "| ghost |"), ["kor: missing", "ghost: not a deck of the run"]),
    (lambda t: t + "| ghost | 5 | 5 | 3 | why |\n", ["ghost: not a deck of the run"]),
    (lambda t: t.replace("| zara | 6 |", "| zara | 10 |"), ["zara: Win 10 is not a whole number from 1 to 9"]),
    (lambda t: t.replace("| zara | 6 | 5 |", "| zara | 6 | 0 |"),
     ["zara: Development 0 is not a whole number from 1 to 9"]),
    (lambda t: t.replace("| zara | 6 | 5 |", "| zara | 6 | 4.5 |"),
     ["zara: Development 4.5 is not a whole number from 1 to 9"]),
    (lambda t: t.replace("| 3 | why A |", "| 3 top | why A |", 1),
     ["zara: Bracket 3 top is not 1 to 5 with ', top' or ', low'"]),
    # the old shape, with Setup, Rebuild and Flow after Development
    (lambda t: t.replace(judgments(), judgments("| Deck | Win | Development | Setup | Rebuild | Flow | Bracket | Why |"))
     .replace(" | 3 | why A |", " | 3 | 4 | 5 | 3 | why A |"), ["zara: 8 cells, not 5", "kor: 8 cells, not 5"]),
], ids=["missing", "extra", "win", "development", "fraction", "bracket", "old columns"])
def test_merge_rankings_rejects_a_faulty_ranker_file(change, faults):
    rankers()
    path = Path("run/rankings-A.md")
    head, _, books = path.read_text().partition("\n## Ledger")
    path.write_text(change(head.rstrip("\n") + "\n") + "\n## Ledger" + books)
    out = run("skills/score-deck/merge_rankings.py", "run")
    assert (out.returncode, out.stderr) == (1, "".join(f"rankings-A.md: {f}\n" for f in faults))
    assert not Path("run/rankings.md").exists()


def test_merge_rankings_computes_the_link_game_changers_and_colours():
    decks()
    Path("moxfield.json").write_text(json.dumps({"user": "owner", "decks": {"z1": "zara"}}))
    oracle = json.loads(read("output/data/oracle.json"))
    oracle["cards"]["Sol Ring"]["game_changer"] = True
    oracle["cards"]["Zara, Tide Caller"]["color_identity"] = ["G", "U", "W"]
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    rankers()
    got = merges("zara: split Win 6/7/3")
    assert got["kor"]["Moxfield"] == "-" and got["zara"]["Moxfield"] == "[Moxfield](https://moxfield.com/decks/z1)"
    assert got["kor"]["Game Changers"] == got["zara"]["Game Changers"] == "Sol Ring"
    assert got["zara"]["Colours"] == "WUG"
    Path("moxfield.json").unlink()
    assert merges("zara: split Win 6/7/3")["zara"]["Moxfield"] == "-"


def declare_cedh():
    """zara's plan with the cEDH line after its Commander bullet"""
    plan = Path("output/decks/zara/plan.md")
    head, _, rest = plan.read_text().partition("- **Commander:**")
    first, _, after = rest.partition("\n")
    plan.write_text(f"{head}- **Commander:**{first}\n- **cEDH:** yes\n{after}")


@pytest.mark.parametrize("zara, stderr", [("5", []), ("4, top", ["zara: bracket 5 by plan"])])
def test_merge_rankings_keeps_5_for_a_plan_declaring_cedh_and_caps_any_other_5(monkeypatch, zara, stderr):
    # A is zara's median ranker, B kor's
    monkeypatch.setitem(OWN, "A", zara)
    monkeypatch.setitem(OWN, "B", "5, low")
    declare_cedh()
    rankers()
    got = merges("zara: split Win 6/7/3", "kor: bracket 5 capped at 4, top", *stderr)
    assert (got["zara"]["Bracket"], got["kor"]["Bracket"]) == ("5", "4, top")


def recomputed():
    """the merged rankings.md beside output/, the run's own copy and ranker files gone, then a recompute"""
    rankers()
    merges("zara: split Win 6/7/3")
    Path("rankings.md").write_text(read("run/rankings.md"))
    for p in Path("run").glob("rankings*.md"): p.unlink()
    return run("skills/score-deck/merge_rankings.py", "--recompute", "run")


def test_recompute_on_an_unchanged_project_reproduces_rankings_md():
    out = recomputed()
    assert (out.returncode, out.stderr) == (0, "")
    assert read("run/rankings.md") == read("rankings.md")


def test_recompute_after_a_salt_change_moves_only_that_decks_card_quality_score_and_place():
    assert recomputed().returncode == 0
    before = ranked()
    oracle = json.loads(read("output/data/oracle.json"))
    oracle["cards"]["Kor Skyfisher"]["salt"] = 0.9
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    for slug in ("zara", "kor"): facts.counts("run", slug, 0)
    assert run("skills/score-deck/merge_rankings.py", "--recompute", "run").returncode == 0
    after = ranked()
    # kor's Commander salt 10: Card quality 18 / 4 = 4.5, (7.4 + 0 + 3.5) / 27 * 100 = 40.37, its Score 40.4 above
    # zara's 34.8
    assert list(after) == ["kor", "zara"]
    assert after["zara"] == before["zara"] | {"#": "2"}
    assert after["kor"] == before["kor"] | {"#": "1", "Commander salt": "10.0", "Card quality": "4.5", "Score": "40.4"}
    assert "| Kor Skyfisher | Card quality | 4.5 | cmdr salt 10, cmdr price 1, 99 salt 6, 99 price 1 | " \
           "Kor Skyfisher 0.90; Kor Skyfisher $1.00 |" in read("run/rankings.md")


def test_recompute_reads_the_speed_table_and_computes_speed_from_it():
    assert recomputed().returncode == 0
    Path("rankings.md").write_text(read("rankings.md").replace("| Zara, Tide Caller | 6.6 | 5.5 |",
                                                               "| Zara, Tide Caller | 10.0 | 5.5 |"))
    assert run("skills/score-deck/merge_rankings.py", "--recompute", "run").returncode == 0
    # Win 10.0 and Development 5.5 as written: Speed 7.75, 7.8; (6.8 + 0 + 4.3) / 27 * 100 = 41.11
    got = ranked()["zara"]
    assert [got[c] for c in ("Win", "Speed", "Score")] == ["10.0", "7.8", "41.1"]


def test_recompute_stops_on_a_rankings_md_without_the_speed_table():
    assert recomputed().returncode == 0
    secs = [s for s in tables.split(read("rankings.md")) if s[0] != "## Speed"]
    Path("rankings.md").write_text(tables.join(secs))
    out = run("skills/score-deck/merge_rankings.py", "--recompute", "run")
    assert (out.returncode, out.stderr) == (1, "rankings.md has no Speed table, rank the decks\n")


def test_recompute_keeps_5_for_a_plan_declaring_cedh_and_caps_any_other_5():
    assert recomputed().returncode == 0
    Path("rankings.md").write_text(read("rankings.md").replace("| W | 4 |", "| W | 5 |"))
    declare_cedh()
    out = run("skills/score-deck/merge_rankings.py", "--recompute", "run")
    assert (out.returncode, out.stderr) == (0, "kor: bracket 5 capped at 4, top\nzara: bracket 5 by plan\n")
    got = ranked()
    assert (got["zara"]["Bracket"], got["kor"]["Bracket"]) == ("5", "4, top")


def test_recompute_stops_on_a_deck_rankings_md_lacks():
    assert recomputed().returncode == 0
    Path("run/ghost-counts.md").write_text(read("run/zara-counts.md"))
    out = run("skills/score-deck/merge_rankings.py", "--recompute", "run")
    assert (out.returncode, out.stderr) == (1, "ghost: not in rankings.md, rank the decks\n")


def article(url):
    """a Wizards article page: its heading and text, then the related articles and footer every page carries"""
    name = url.rsplit("/", 1)[1]
    return (f"<html><nav>menu</nav><article><h1><span>{name}</span></h1><p>About {name}.</p><h3>Brackets</h3>"
            f"<ul><li>Bracket 1</li></ul></article><aside><h3>Related</h3></aside><footer>legal</footer></html>").encode()


@pytest.fixture
def wizards(monkeypatch):
    """Wizards answering each article URL with its page, the URLs asked kept in order"""
    asked = []
    def get(url): asked.append(url); return article(url)
    monkeypatch.setattr(fetch_syntax, "get", get)
    return asked


def test_fetch_brackets_writes_one_section_per_article_and_fetches_once(wizards, capsys):
    fetch_brackets.main()
    assert wizards == fetch_brackets.PAGES
    text = read("output/data/brackets.md")
    assert text.startswith("## introducing-commander-brackets-beta\n\n"
                           f"Source: {fetch_brackets.PAGES[0]}\n\nAbout introducing-commander-brackets-beta.\n\n"
                           "#### Brackets\n\n- Bracket 1\n\n## commander-brackets-beta-update-april-22-2025\n")
    assert text.count("\n## ") == 3 and "Related" not in text and "legal" not in text
    first = fetch_brackets.sections(text)[fetch_brackets.PAGES[0]]
    assert capsys.readouterr().out.splitlines()[0] == f"## introducing-commander-brackets-beta  ({len(first)} characters)"
    fetch_brackets.main()
    assert wizards == fetch_brackets.PAGES and read("output/data/brackets.md") == text


def test_fetch_brackets_fetches_only_an_added_article(wizards, monkeypatch):
    fetch_brackets.main()
    later = fetch_brackets.NEWS + "commander-brackets-update-later"
    monkeypatch.setattr(fetch_brackets, "PAGES", fetch_brackets.PAGES + [later])
    wizards.clear()
    fetch_brackets.main()
    assert wizards == [later]
    assert read("output/data/brackets.md").endswith(f"## commander-brackets-update-later\n\nSource: {later}\n\n"
                                                    "About commander-brackets-update-later.\n\n#### Brackets\n\n- Bracket 1\n")


@pytest.mark.parametrize("answer, why", [(HTTPError("u", 403, "Forbidden", {}, None), "HTTP 403"),
                                         (b"<title>Just a moment...</title>", "Cloudflare challenge")],
                         ids=["403", "challenge"])
def test_fetch_brackets_stops_naming_a_refused_url(monkeypatch, answer, why):
    def get(url):
        if isinstance(answer, BaseException): raise answer
        return answer
    monkeypatch.setattr(fetch_syntax, "get", get)
    with pytest.raises(SystemExit, match=f"^{fetch_brackets.PAGES[0]}: {why}$"):
        fetch_brackets.main()
    assert not Path("output/data/brackets.md").exists()
