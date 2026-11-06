import copy, json
from pathlib import Path
import pytest
from conftest import run, read
import facts, merge, merge_rankings, project, settings, tables

# each card's score from scorers A, B and C
SCORES = {
    "Nonlands": {"Zara, Tide Caller": (10, 10, 9), "Sol Ring": (8, 8, 8), "Tidal Insight": (7, 6, 8),
                 "Kelp Weaver": (6, 6, 6), "Brine Elemental": (2, 5, 6), "Coral Signet": (4, 4, 4),
                 "Wave Breaker": (3, 2, 3)},
    "Lands": {"Sunken Grotto": (7, 7, 7), "Island (4)": (6, 6, 6), "Misty Cove": (5, 4, 4)},
    "Adds": {"Deep Current": (8, 8, 7), "Tidepool Ruins": (6, 6, 6)},
}
# each card's role, or its role from scorers A, B and C
ROLES = {"Zara, Tide Caller": "commander", "Sol Ring": "ramp", "Tidal Insight": "draw",
         "Kelp Weaver": ("engine", "draw", "threat"), "Brine Elemental": ("threat", "fodder", "fodder"),
         "Coral Signet": "ramp", "Wave Breaker": "threat", "Sunken Grotto": "land", "Island (4)": "land",
         "Misty Cove": "land", "Deep Current": "engine", "Tidepool Ruins": "land", "Pearl Diver": "threat", "Tundra": "land"}


def scorers(letters="ABC", scores=SCORES):
    """one scorer file per letter, each in its own run/work-x-<letter>/ subfolder, as the scorer agent shapes them"""
    for i, letter in enumerate(letters):
        text = f"# Zara, Tide Caller: fit scores ({letter})\n"
        for section, cards in scores.items():
            text += f"\n## {section}\n| Card | Score | Role | Note |\n|---|---|---|---|\n"
            text += "".join(f"| {card} | {s[i]} | {role(card, i)} | fits |\n" for card, s in cards.items())
        Path(f"run/work-x-{letter}").mkdir(parents=True)
        Path(f"run/work-x-{letter}/zara.md").write_text(text + "\n## Shape\nignored\n")


def role(card, i):
    r = ROLES[card]; return r if isinstance(r, str) else r[i]


def without_roles(path):
    """a deck file as written before the Role column: no Role cell in its Cards and Adds tables, no Roles line"""
    lines = [l.split("|") for l in read(path).split("\n## Roles\n")[0].splitlines()]
    Path(path).write_text("\n".join("|".join(c[:3] + c[4:] if len(c) in (6, 8) else c) for c in lines) + "\n")
    return read(path)


def test_parse_reads_every_section():
    scorers("A")
    got = merge.parse("run/work-x-A/zara.md")
    assert got["Island"] == ("Island (4)", 6, "land", "fits", "lands")
    assert got["Deep Current"] == ("Deep Current", 8, "engine", "fits", "adds")
    assert got["Zara, Tide Caller"][4] == "nonlands"
    assert len(got) == 12


def test_key_and_copies():
    assert project.key("4 Island (4)") == "Island"
    assert project.key("Rising Tide // Tidal Flats") == "Rising Tide"
    assert project.copies("Island (4)") == 4 and project.copies("Island x 3") == 3 and project.copies("Sol Ring") == 1


def test_a_deck_with_no_list_stops_naming_the_file():
    with pytest.raises(SystemExit) as stop: project.decklist("nodeck")
    assert stop.value.code == "no output/decks/nodeck/list.txt"


@pytest.mark.parametrize("plan", [None, "- **Win:** Out-card: Zara, Tide Caller + Tidal Insight. Draws the table out.\n"])
def test_merge_titles_a_deck_with_no_plan_or_no_heading_from_its_list(plan):
    scorers()
    Path("output/decks/zara/plan.md").unlink() if plan is None else Path("output/decks/zara/plan.md").write_text(plan)
    out = run("skills/score/merge.py", "run", "zara")
    assert out.returncode == 0, out.stderr
    assert read("run/merged/zara/nonlands.md").startswith("# Zara, Tide Caller: nonlands\n")


def test_merge_writes_the_file_pair():
    scorers()
    out = run("skills/score/merge.py", "run", "zara")
    assert out.returncode == 0, out.stderr
    assert out.stderr.startswith("zara: 10: 1 / 8-9: 1 / 5-7: ") and out.stderr.endswith("3 scorers. 1 flagged\n")
    assert read("run/merged/zara/nonlands.md") == """# Zara, Tide Caller: nonlands

## Cards
| Card | Score | Role | Note |
|---|---|---|---|
| Zara, Tide Caller | 10 | commander | fits |
| Sol Ring | 8 | ramp | fits |
| Tidal Insight | 7 | draw | fits |
| Kelp Weaver | 6 | engine | fits |
| Brine Elemental | 5 | fodder | fits |
| Coral Signet | 4 | ramp | fits |
| Wave Breaker | 3 | threat | fits |

## Adds
Built 2025-01-01, last edited 2025-06-01, bracket 2.

| Card | Score | Role | Note | New | ~Price |
|---|---|---|---|---|---|
| Deep Current | 8 | engine | fits | Yes | $1.50 |

## Cuts
| Card | Score | Why it underperforms here |
|---|---|---|
| Wave Breaker | 3 | Aggro body in a control deck |

## Shape
10: 1 / 8-9: 1 / 5-7: 3 / 4 or below: 2, mean 6.1 (by card copy), 3 scorers.

## Roles
ramp 2 · commander 1 · draw 1 · engine 1 · fodder 1 · threat 1 · lands 6
"""
    lands = read("run/merged/zara/lands.md")
    assert "| Island (4) | 6 | land | fits |" in lands
    assert "| Tidepool Ruins | 6 | land | fits | No | $0.40 |" in lands
    assert "| Misty Cove | 4 | Enters tapped for no gain |" in lands   # the cut takes this run's score
    assert lands.endswith("mean 5.8 (by card copy), 3 scorers.\n") and "## Roles" not in lands
    flagged = read("run/zara-flagged.md")
    assert "## Brine Elemental\nScores A/B/C: [2, 5, 6]\n" in flagged and "Sol Ring" not in flagged


def test_one_scorer_stands_alone():
    scorers("A")
    out = run("skills/score/merge.py", "run", "zara")
    assert out.stderr.endswith("1 scorer.\n")
    assert not Path("run/zara-flagged.md").exists()
    assert "| Brine Elemental | 2 | threat | fits |" in read("run/merged/zara/nonlands.md")


def test_a_scorer_file_in_the_run_folder_itself_is_ignored():
    scorers("A")
    Path("run/zara-A.md").write_text(read("run/work-x-A/zara.md").replace("| Brine Elemental | 2 |", "| Brine Elemental | 9 |"))
    out = run("skills/score/merge.py", "run", "zara")
    assert out.returncode == 0 and out.stderr.endswith("1 scorer.\n"), out.stderr
    assert "| Brine Elemental | 2 | threat | fits |" in read("run/merged/zara/nonlands.md")


def test_card_only_score_patches_the_deck_files():
    with open("output/decks/zara/list.txt", "a") as f: f.write("1 Deep Current\n")
    nonlands, lands = read("output/decks/zara/nonlands.md"), read("output/decks/zara/lands.md")
    scorers(scores={"Nonlands": {"Kelp Weaver": (7, 7, 6), "Deep Current": (8, 8, 5)}})
    out = run("skills/score/merge.py", "run", "zara", "Kelp Weaver", "deep current")
    assert out.returncode == 0, out.stderr
    assert out.stderr == "zara: 10: 1 / 8-9: 2 / 5-7: 9 / 4 or below: 2, mean 6.3 (by card copy), 3 scorers. 1 flagged\n"
    assert read("run/merged/zara/nonlands.md") == (nonlands
        .replace("| Kelp Weaver | 6 | draw | Blocker that loots |\n", "")
        .replace("| Tidal Insight | 7 | draw | Instant draw two |\n", "| Deep Current | 8 | engine | fits |\n"
                 "| Tidal Insight | 7 | draw | Instant draw two |\n| Kelp Weaver | 7 | engine | fits |\n")
        .replace("| Deep Current | 7 | engine | A card on every spell, stacks with Zara | Yes | $1.50 |\n", "")
        .replace("10: 1 / 8-9: 1 / 5-7: 3 / 4 or below: 2, mean 6.1", "10: 1 / 8-9: 2 / 5-7: 3 / 4 or below: 2, mean 6.5")
        .replace("draw 2 · ramp 2 · threat 2 · commander 1 · lands 6", "engine 2 · ramp 2 · threat 2 · commander 1 · draw 1 · lands 6"))
    assert read("run/merged/zara/lands.md") == lands
    assert "## Deep Current\nScores A/B/C: [8, 8, 5]\n" in read("run/zara-flagged.md")


def test_card_only_score_puts_a_candidate_in_its_adds_table():
    nonlands, lands = read("output/decks/zara/nonlands.md"), read("output/decks/zara/lands.md")
    scorers(scores={"Nonlands": {"Kelp Weaver": (7, 7, 6), "Pearl Diver": (6, 6, 5), "Tundra": (8, 8, 7)},
                    "Adds": {"Deep Current": (8, 8, 5)}})
    out = run("skills/score/merge.py", "run", "zara", "Kelp Weaver", "Pearl Diver", "Tundra", "Deep Current")
    assert out.returncode == 0, out.stderr
    assert out.stderr == "zara: 10: 1 / 8-9: 1 / 5-7: 9 / 4 or below: 2, mean 6.2 (by card copy), 3 scorers. 1 flagged\n"
    assert read("run/merged/zara/nonlands.md") == (nonlands
        .replace("| Kelp Weaver | 6 | draw | Blocker that loots |\n", "| Kelp Weaver | 7 | engine | fits |\n")
        .replace("| Deep Current | 7 | engine | A card on every spell, stacks with Zara | Yes | $1.50 |\n",
                 "| Deep Current | 8 | engine | fits | Yes | $1.50 |\n| Pearl Diver | 6 | threat | fits | - | - |\n")
        .replace("mean 6.1", "mean 6.3")
        .replace("draw 2 · ramp 2 · threat 2 · commander 1 · lands 6", "ramp 2 · threat 2 · commander 1 · draw 1 · engine 1 · lands 6"))
    assert read("run/merged/zara/lands.md") == lands.replace(
        "| Tidepool Ruins |", "| Tundra | 8 | land | fits | - | - |\n| Tidepool Ruins |")


def test_a_candidate_makes_the_adds_table_it_lacks():
    lands = read("output/decks/zara/lands.md")
    bare = lands[:lands.index("## Adds")] + lands[lands.index("## Shape"):]
    Path("output/decks/zara/lands.md").write_text(bare)
    scorers(scores={"Lands": {"Tundra": (8, 8, 7)}})
    assert run("skills/score/merge.py", "run", "zara", "Tundra").returncode == 0
    assert read("run/merged/zara/lands.md") == bare.replace("## Shape", """## Adds

| Card | Score | Role | Note | New | ~Price |
|---|---|---|---|---|---|
| Tundra | 8 | land | fits | - | - |

## Shape""")


def test_card_mode_patches_only_the_named_cards():
    scorers(scores={"Nonlands": {"Kelp Weaver": (7, 7, 6), "Sol Ring": (1, 1, 1)}})
    assert run("skills/score/merge.py", "run", "zara", "Kelp Weaver").returncode == 0
    nonlands = read("run/merged/zara/nonlands.md")
    assert "| Kelp Weaver | 7 | engine | fits |" in nonlands and "| Sol Ring | 8 | ramp |" in nonlands


def test_card_mode_reads_a_file_without_the_role_column():
    nonlands, lands = without_roles("output/decks/zara/nonlands.md"), without_roles("output/decks/zara/lands.md")
    assert "Role" not in nonlands + lands and "| Misty Cove | 5 | Enters tapped for no gain |" in lands
    assert "| Card | Score | Note | New | ~Price |\n|---|---|---|---|---|\n| Deep Current | 7 | A card" in nonlands
    scorers(scores={"Nonlands": {"Kelp Weaver": (7, 7, 6)}})
    assert run("skills/score/merge.py", "run", "zara", "Kelp Weaver").returncode == 0
    assert read("run/merged/zara/nonlands.md") == """# Zara, Tide Caller: nonlands

## Cards
| Card | Score | Role | Note |
|---|---|---|---|
| Zara, Tide Caller | 10 | - | Commander engine: a card on every spell |
| Sol Ring | 8 | - | Fast mana |
| Tidal Insight | 7 | - | Instant draw two |
| Kelp Weaver | 7 | engine | fits |
| Brine Elemental | 5 | - | Big body, no synergy |
| Coral Signet | 4 | - | Slow rock |
| Wave Breaker | 3 | - | Aggro body in a control deck |

## Adds
Built 2025-01-01, last edited 2025-06-01, bracket 2.

| Card | Score | Role | Note | New | ~Price |
|---|---|---|---|---|---|
| Deep Current | 7 | - | A card on every spell, stacks with Zara | Yes | $1.50 |

## Cuts
| Card | Score | Why it underperforms here |
|---|---|---|
| Wave Breaker | 3 | Aggro body in a control deck |

## Shape
10: 1 / 8-9: 1 / 5-7: 3 / 4 or below: 2, mean 6.3 (by card copy), 3 scorers.

## Roles
engine 1
"""
    assert "| Island (4) | 6 | - | Basic |" in read("run/merged/zara/lands.md")


def test_a_card_the_scorers_lack_stops_the_run_naming_it():
    scorers(scores={k: {c: s for c, s in v.items() if c not in ("Sol Ring", "Misty Cove")} for k, v in SCORES.items()})
    out = run("skills/score/merge.py", "run", "zara")
    assert (out.returncode, out.stderr) == (1, "zara: not in the scorer files: Misty Cove, Sol Ring\n")
    out = run("skills/score/merge.py", "run", "zara", "Kelp Weaver", "Pearl Diver")
    assert (out.returncode, out.stderr) == (1, "zara: not in the scorer files: Pearl Diver\n")
    assert not Path("run/merged").exists()


def test_tables_prints_the_adds_names_alone():
    out = run("lib/tables.py", "zara")
    assert (out.returncode, out.stdout) == (0, "Deep Current\nTidepool Ruins\n")
    assert run("lib/tables.py").returncode == 1

def test_settings_defaults():
    Path("settings.json").unlink()
    defaults = copy.deepcopy(settings.DEFAULTS)
    assert settings.settings() == defaults
    Path("settings.json").write_text('{"scorers": 1, "quota": {"adds": 15}, "cart": {"finish": "nonfoil"}, '
                                     '"models": {"researcher": "claude-sonnet-5-5"}}')
    assert settings.settings() == {**defaults, "scorers": 1, "quota": {**defaults["quota"], "adds": 15},
                                   "cart": {**defaults["cart"], "finish": "nonfoil"},
                                   "models": {**defaults["models"], "researcher": "claude-sonnet-5-5"}}
    assert settings.DEFAULTS == defaults


def test_settings_overrides():
    base, given, defaults = settings.settings(), read("settings.json"), copy.deepcopy(settings.DEFAULTS)
    got = settings.settings(["scorers=1", "quota.adds=15", "quota.cuts=[8, 12]", "cart.finish=nonfoil",
                             "models.scorer=claude-opus-5-5", "rankers=1"])
    assert got == {**base, "scorers": 1, "rankers": 1, "models": {**base["models"], "scorer": "claude-opus-5-5"},
                   "quota": {**base["quota"], "adds": 15, "cuts": [8, 12]}, "cart": {**base["cart"], "finish": "nonfoil"}}
    assert settings.settings() == base and read("settings.json") == given and settings.DEFAULTS == defaults
    out = run("lib/settings.py", "budget=50", "universes_beyond=false", "new_sets=true")
    assert out.returncode == 0 and '"budget": 50' in out.stdout and '"universes_beyond": false' in out.stdout
    assert '"new_sets": true' in out.stdout


@pytest.mark.parametrize("text, said", [
    ('{"scorers": 1,}', None), ("[1]", "not an object"), ('{"models": "x"}', "models must be an object"),
    ('{"budget": "50"}', "budget must be a number or null"), ('{"budget": true}', "budget must be a number or null"),
    ('{"scorers": 0}', "scorers must be a whole number ≥ 1"), ('{"rankers": 2.5}', "rankers must be a whole number ≥ 1"),
    ('{"images": "yes"}', "images must be true or false")])
def test_a_malformed_settings_json_stops_with_one_line(text, said):
    Path("settings.json").write_text(text)
    if said is None:   # not JSON: json's own error, its wording Python's
        with pytest.raises(ValueError) as error: json.loads(text)
        said = str(error.value)
    out = run("lib/settings.py")
    assert (out.returncode, out.stdout, out.stderr) == (1, "", f"settings.json: {said}\n")


@pytest.mark.parametrize("word, said", [("scorers=0", "scorers must be a whole number ≥ 1"),
                                        ("models=x", "models must be an object"),
                                        ("budget=fifty", "budget must be a number or null"),
                                        ("new_sets=1", "new_sets must be true or false")])
def test_an_override_of_the_wrong_kind_stops_naming_the_word(word, said):
    out = run("lib/settings.py", word)
    assert (out.returncode, out.stdout, out.stderr) == (1, "", f"{word}: {said}\n")


def test_an_unknown_settings_key_is_named_and_ignored():
    Path("settings.json").write_text('{"ranker": 5, "budget": 20}')
    out = run("lib/settings.py")
    assert (out.returncode, out.stderr) == (0, "settings.json: unknown key ranker\n")
    assert '"budget": 20' in out.stdout


# each deck's Speed, Resilience and Interaction from rankers A to E; zara's Salt is 4, kor's 3
JUDGED = {"zara": {"A": [7, 5, 5], "B": [6, 4, 5], "C": [3, 5, 9]},
          "kor": {"A": [5, 5, 5], "B": [8, 8, 8], "C": [8, 8, 8]}}
OWN = {x: (b, k) for x, b, k in zip("ABCDE", ["3", "4", "2", "3, top", "3"], ["6-7", "5", "8", "7", "6"])}
JUDGMENTS_RULE = "|---|---|---|---|---|---|---|"


def decks(salts={"Zara, Tide Caller": 0.525, "Kor Skyfisher": 0.45}):
    """the fixture with a second deck, kor, the commanders given colours and these salts, moxfield.json naming both,
    and run/ holding both decks' counts files"""
    oracle = json.loads(read("output/data/oracle.json"))
    oracle["cards"]["Kor Skyfisher"] = {"name": "Kor Skyfisher", "type_line": "Creature — Kor Bird Soldier",
                                        "color_identity": ["W"]}
    oracle["cards"]["Zara, Tide Caller"]["color_identity"] = ["U"]
    for name, value in salts.items(): oracle["cards"][name]["salt"] = value
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    Path("output/decks/kor").mkdir()
    Path("output/decks/kor/list.txt").write_text("1 Kor Skyfisher\n\n1 Sol Ring\n9 Island\n")
    Path("moxfield.json").write_text(json.dumps({"user": "owner", "decks": {"z1": "zara", "k1": "kor"}}))
    Path("run").mkdir(exist_ok=True)
    for slug in ("zara", "kor"): facts.counts("run", slug)


def ledger(slug, x):
    """ranker x's Ledger rows for one deck, each naming the ranker"""
    return [f"| {slug} | {c} | 5 | count {x} | cards {x} |" for c in ("Resilience", "Interaction")]


def rankers(judged=JUDGED, letters="ABC", order=None):
    """one run/rankings-<letter>.md per letter in the ranker agent's shape, its decks in order[letter] or strongest
    first by its own values; makes the decks first"""
    if not Path("run").exists(): decks()
    for x in letters:
        slugs = (order or {}).get(x) or sorted(judged, key=lambda d: -sum(judged[d][x]))
        rows = "".join(f"| {d} | {' | '.join(map(str, judged[d][x]))} | {OWN[x][1]} | {OWN[x][0]} | why {x} |\n"
                       for d in slugs)
        books = "".join(f"{l}\n" for d in slugs for l in ledger(d, x))
        Path(f"run/rankings-{x}.md").write_text(f"# Judgments ({x})\n\n{merge_rankings.JUDGMENTS}\n{JUDGMENTS_RULE}\n"
                                                f"{rows}\n## Ledger\n\n| Deck | Criterion | Value | Count | Cards |\n"
                                                f"|---|---|---|---|---|\n{books}")


def ranked():
    """run/rankings.md as {slug: {column: cell}}, its Rankings and Criteria columns, its decks in order"""
    secs = dict(tables.split(read("run/rankings.md")))
    heads = lambda h: [c.strip() or "Moxfield" for c in h.strip("|").split("|")]
    crit = {r[0]: dict(zip(heads(merge_rankings.CRITERIA), r)) for r in tables.cells(secs["## Criteria"])}
    return {r[1].split("decks/")[1].rstrip("/)"): crit[r[0]] | dict(zip(heads(merge_rankings.RANKINGS), r))
            for r in tables.cells(secs[None])}


def merges(*stderr):
    """ranked() after a merge that succeeds printing these lines"""
    out = run("skills/score/merge_rankings.py", "run")
    assert (out.returncode, out.stderr) == (0, "".join(f"{l}\n" for l in stderr))
    return ranked()


def test_merge_rankings_takes_the_mean_of_three_rankers_and_computes_the_rest():
    rankers()
    merges("zara: split Speed 7/6/3, Interaction 5/5/9")
    # zara's criteria 5.3, 4.7, 6.3 and Salt 4, their mean 5.075, its Score 50.9; its own Scores 53.1, 46.9 and 53.1
    # make A the median; kor's 7.0 three times and Salt 3, 62.5, its own 43.8, 71.9 and 71.9 make B the median
    assert read("run/rankings.md") == f"""# Rankings

{merge_rankings.RANKINGS}
|---|---|---|---|---|---|---|---|---|
| 1 | [Kor Skyfisher](output/decks/kor/) | W | 4 | 62.5 | 5 | none | why B | [Moxfield](https://moxfield.com/decks/k1) |
| 2 | [Zara, Tide Caller](output/decks/zara/) | U | 3 | 50.9 | 6-7 | none | why A | [Moxfield](https://moxfield.com/decks/z1) |

## Criteria

{merge_rankings.CRITERIA}
|---|---|---|---|---|---|
| 1 | Kor Skyfisher | 7.0 | 7.0 | 7.0 | 3.0 |
| 2 | Zara, Tide Caller | 5.3 | 4.7 | 6.3 | 4.0 |

## Ledger

{merge_rankings.LEDGER}
|---|---|---|---|---|
| Kor Skyfisher | Resilience | 5 | count B | cards B |
| Kor Skyfisher | Interaction | 5 | count B | cards B |
| Kor Skyfisher | Salt | 3 | mean 0.45 over 1 cards | - |
| Zara, Tide Caller | Resilience | 5 | count A | cards A |
| Zara, Tide Caller | Interaction | 5 | count A | cards A |
| Zara, Tide Caller | Salt | 4 | mean 0.53 over 1 cards | - |
"""


def test_merge_rankings_takes_the_middle_three_of_five_and_the_median_rankers_cells():
    # Speed 1 5 6 7 9 keeps 5 6 7, Resilience 3 3 4 9 9 keeps 3 4 9; own Scores 28.1 71.9 40.6 46.9 65.6 make D the median
    five = {"zara": {"A": [1, 3, 5], "B": [9, 9, 5], "C": [5, 3, 5], "D": [6, 4, 5], "E": [7, 9, 5]},
            "kor": {x: [5, 5, 5] for x in "ABCDE"}}
    rankers(five, "ABCDE")
    got = merges("zara: split Speed 1/9/5/6/7, Resilience 3/9/3/4/9")["zara"]
    # (6.0 + 5.3 + 5.0 + 4) / 4 = 5.075, its Score 50.9
    assert [got[c] for c in ("Speed", "Resilience", "Interaction", "Salt", "Score", "Bracket", "Kill turn", "Why")] == \
        ["6.0", "5.3", "5.0", "4.0", "50.9", "3, top", "7", "why D"]
    assert "| Zara, Tide Caller | Resilience | 5 | count D | cards D |" in read("run/rankings.md")


def test_merge_rankings_rounds_a_mean_of_two_or_four_half_up():
    rankers({"zara": {"A": [5, 4, 5], "B": [6, 5, 5]}, "kor": {x: [5, 5, 5] for x in "AB"}}, "AB")
    assert [merges()["zara"][c] for c in ("Speed", "Resilience")] == ["5.5", "4.5"]
    rankers({"zara": {"A": [5, 5, 5], "B": [5, 5, 5], "C": [5, 5, 5], "D": [6, 5, 5]},
             "kor": {x: [5, 5, 5] for x in "ABCD"}}, "ABCD")
    assert merges()["zara"]["Speed"] == "5.3"  # 21 / 4 = 5.25


def test_merge_rankings_rounds_a_score_ending_in_5_up():
    # Speed and Resilience 5 6 6, 5.7 each, Interaction 5.0 and Salt 4: (20.4 / 4 - 1) / 8 * 100 = 51.25
    rankers({"zara": {"A": [5, 5, 5], "B": [6, 6, 5], "C": [6, 6, 5]}, "kor": {x: [5, 5, 5] for x in "ABC"}})
    assert merges()["zara"]["Score"] == "51.3"


def test_merge_rankings_breaks_a_tie_by_mean_place_then_by_slug():
    same = {"zara": {x: [5, 5, 5] for x in "ABC"}, "kor": {x: [5, 5, 5] for x in "ABC"}}
    decks({"Zara, Tide Caller": 0.45, "Kor Skyfisher": 0.45})
    rankers(same, order={"A": ["zara", "kor"], "B": ["zara", "kor"], "C": ["kor", "zara"]})
    assert list(merges()) == ["zara", "kor"]
    for x in "ABC": Path(f"run/rankings-{x}.md").unlink()
    rankers(same, "AB", order={"A": ["zara", "kor"], "B": ["kor", "zara"]})
    assert list(merges()) == ["kor", "zara"]


def test_one_ranker_goes_through_the_merge():
    rankers(letters="B")
    got = merges()
    # kor 8, 8, 8 and Salt 3: 71.9; zara 6, 4, 5 and Salt 4: 46.9
    assert [(d, got[d]["Score"], got[d]["Speed"], got[d]["Why"]) for d in got] == \
        [("kor", "71.9", "8.0", "why B"), ("zara", "46.9", "6.0", "why B")]


@pytest.mark.parametrize("change, faults", [
    (lambda t: t.replace("| kor |", "| ghost |"), ["kor: missing", "ghost: not a deck of the run"]),
    (lambda t: t + "| ghost | 5 | 5 | 5 | 6 | 3 | why |\n", ["ghost: not a deck of the run"]),
    (lambda t: t.replace("| zara | 7 |", "| zara | 10 |"), ["zara: Speed 10 is not a whole number from 1 to 9"]),
    (lambda t: t.replace("| 6-7 | 3 |", "| 6-7 | 3 top |", 1),
     ["zara: Bracket 3 top is not 1 to 5 with ', top' or ', low'"]),
])
def test_merge_rankings_rejects_a_faulty_ranker_file(change, faults):
    rankers()
    path = Path("run/rankings-A.md")
    head, _, books = path.read_text().partition("\n## Ledger")
    path.write_text(change(head.rstrip("\n") + "\n") + "\n## Ledger" + books)
    out = run("skills/score/merge_rankings.py", "run")
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
    got = merges("zara: split Speed 7/6/3, Interaction 5/5/9")
    assert got["kor"]["Moxfield"] == "-" and got["zara"]["Moxfield"] == "[Moxfield](https://moxfield.com/decks/z1)"
    assert got["kor"]["Game Changers"] == got["zara"]["Game Changers"] == "Sol Ring"
    assert got["zara"]["Colours"] == "WUG"
    Path("moxfield.json").unlink()
    assert merges("zara: split Speed 7/6/3, Interaction 5/5/9")["zara"]["Moxfield"] == "-"
