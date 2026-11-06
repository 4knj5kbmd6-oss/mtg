import copy
from pathlib import Path
from conftest import run, read
import merge, merge_rankings, project, settings

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
    assert defaults["scorers"] == 3 and defaults["rankers"] == 3
    sonnet = "claude-sonnet-5-5"
    assert defaults["models"] == {"scorer": sonnet, "ranker": sonnet, "researcher": "claude-opus-5-5", "judge": sonnet,
                                  "librarian": sonnet, "shopper": sonnet, "planner": "claude-opus-5-5"}
    Path("settings.json").write_text('{"scorers": 1, "quota": {"adds": 15}, "cart": {"finish": "nonfoil"}, '
                                     '"models": {"researcher": "claude-sonnet-5-5"}}')
    assert settings.settings() == {**defaults, "scorers": 1, "quota": {**defaults["quota"], "adds": 15},
                                   "cart": {**defaults["cart"], "finish": "nonfoil"},
                                   "models": {**defaults["models"], "researcher": sonnet}}
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


# each deck's Score and three criteria from rankers A, B and C, and each ranker's own Bracket and Kill turn
RANKS = {"zara": {"A": (60, [7, 5, 5]), "B": (50, [6, 4, 5]), "C": (70, [3, 5, 9])},
         "kor": {"A": (50, [5] * 3), "B": (88, [8] * 3), "C": (75, [8] * 3)}}
NAMES = {"zara": ("Zara, Tide Caller", "U"), "kor": ("Kor Skyfisher", "W")}
OWN = {x: (b, k) for x, b, k in zip("ABCDE", "34233", ["6-7", "5", "8", "7", "6"])}
RULE = "|---|---|---|---|---|---|---|---|---|"
CRIT_RULE = "|---|---|---|---|---|"


def ledger(name, x):
    """ranker x's Ledger rows for one deck, each naming the ranker"""
    return [f"| {name} | {c} | 5 | count {x} | cards {x} |" for c in ("Resilience", "Interaction")]


def rankers(ranks=RANKS, letters="ABC"):
    """one run/rankings-<letter>.md per letter, as the ranker agent shapes it, its rows by its own Score"""
    Path("run").mkdir()
    for x in letters:
        decks = sorted(ranks, key=lambda d: -ranks[d][x][0])
        rows = "".join(f"| {i} | [{NAMES[d][0]}](output/decks/{d}/) | {NAMES[d][1]} | {OWN[x][0]} | {ranks[d][x][0]} | "
                       f"{OWN[x][1]} | none | why {x} | [Moxfield](https://moxfield.com/decks/{d}) |\n"
                       for i, d in enumerate(decks, 1))
        crit = "".join(f"| {i} | {NAMES[d][0]} | {' | '.join(map(str, ranks[d][x][1]))} |\n" for i, d in enumerate(decks, 1))
        books = "".join(f"{l}\n" for d in decks for l in ledger(NAMES[d][0], x))
        Path(f"run/rankings-{x}.md").write_text(f"# Rankings\n\n{merge_rankings.RANKINGS}\n{RULE}\n{rows}\n"
                                                f"## Criteria\n\n{merge_rankings.CRITERIA}\n{CRIT_RULE}\n{crit}\n"
                                                f"## Ledger\n\n{merge_rankings.LEDGER}\n|---|---|---|---|---|\n{books}")


def test_merge_rankings_takes_the_mean_of_three_rankers():
    rankers()
    out = run("skills/score/merge_rankings.py", "run")
    assert out.returncode == 0
    assert out.stderr == "zara: split Speed 7/6/3, Interaction 5/5/9\n"
    # zara's criteria 5.3, 4.7 and 6.3, their mean 5.43, its Score 55.4; kor's each 7.0
    assert read("run/rankings.md") == f"""# Rankings

{merge_rankings.RANKINGS}
{RULE}
| 1 | [Kor Skyfisher](output/decks/kor/) | W | 2 | 75.0 | 8 | none | why C | [Moxfield](https://moxfield.com/decks/kor) |
| 2 | [Zara, Tide Caller](output/decks/zara/) | U | 3 | 55.4 | 6-7 | none | why A | [Moxfield](https://moxfield.com/decks/zara) |

## Criteria

{merge_rankings.CRITERIA}
{CRIT_RULE}
| 1 | Kor Skyfisher | 7.0 | 7.0 | 7.0 |
| 2 | Zara, Tide Caller | 5.3 | 4.7 | 6.3 |

## Ledger

{merge_rankings.LEDGER}
|---|---|---|---|---|
""" + "".join(f"{l}\n" for l in ledger("Kor Skyfisher", "C") + ledger("Zara, Tide Caller", "A"))


def test_merge_rankings_takes_the_middle_three_of_five_and_the_median_rankers_ledger():
    # Speed 1 5 6 7 9 keeps 5 6 7, Resilience 3 3 4 9 9 keeps 3 4 9; Scores 70 60 30 50 40 make D the median
    five = {"zara": {"A": (70, [1, 3, 5]), "B": (60, [9, 9, 5]), "C": (30, [5, 3, 5]), "D": (50, [6, 4, 5]),
                     "E": (40, [7, 9, 5])}}
    rankers(five, "ABCDE")
    out = run("skills/score/merge_rankings.py", "run")
    assert out.returncode == 0
    assert out.stderr == "zara: split Speed 1/9/5/6/7, Resilience 3/9/3/4/9\n"
    text = read("run/rankings.md")
    # (6.0 + 5.3 + 5.0) / 3 = 5.43, its Score 55.4
    assert "| 1 | [Zara, Tide Caller](output/decks/zara/) | U | 3 | 55.4 | 7 | none | why D |" in text
    assert "| 1 | Zara, Tide Caller | 6.0 | 5.3 | 5.0 |" in text
    assert text.endswith("|---|---|---|---|---|\n" + "".join(f"{l}\n" for l in ledger("Zara, Tide Caller", "D")))


def test_one_ranker_is_copied_as_it_is():
    rankers(letters="B")
    assert run("skills/score/merge_rankings.py", "run").returncode == 0
    assert read("run/rankings.md") == read("run/rankings-B.md")
