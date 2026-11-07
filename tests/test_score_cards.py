import copy, json
from pathlib import Path
import pytest
from conftest import run, read
import merge, project, settings

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
    out = run("skills/score-cards/merge.py", "run", "zara")
    assert out.returncode == 0, out.stderr
    assert read("run/merged/zara/nonlands.md").startswith("# Zara, Tide Caller: nonlands\n")


def test_merge_writes_the_file_pair():
    scorers()
    out = run("skills/score-cards/merge.py", "run", "zara")
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
Built 2025-01-01, last edited 2025-06-01.

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
    out = run("skills/score-cards/merge.py", "run", "zara")
    assert out.stderr.endswith("1 scorer.\n")
    assert not Path("run/zara-flagged.md").exists()
    assert "| Brine Elemental | 2 | threat | fits |" in read("run/merged/zara/nonlands.md")


def test_a_scorer_file_in_the_run_folder_itself_is_ignored():
    scorers("A")
    Path("run/zara-A.md").write_text(read("run/work-x-A/zara.md").replace("| Brine Elemental | 2 |", "| Brine Elemental | 9 |"))
    out = run("skills/score-cards/merge.py", "run", "zara")
    assert out.returncode == 0 and out.stderr.endswith("1 scorer.\n"), out.stderr
    assert "| Brine Elemental | 2 | threat | fits |" in read("run/merged/zara/nonlands.md")


def test_card_only_score_patches_the_deck_files():
    with open("output/decks/zara/list.txt", "a") as f: f.write("1 Deep Current\n")
    nonlands, lands = read("output/decks/zara/nonlands.md"), read("output/decks/zara/lands.md")
    scorers(scores={"Nonlands": {"Kelp Weaver": (7, 7, 6), "Deep Current": (8, 8, 5)}})
    out = run("skills/score-cards/merge.py", "run", "zara", "Kelp Weaver", "deep current")
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
    out = run("skills/score-cards/merge.py", "run", "zara", "Kelp Weaver", "Pearl Diver", "Tundra", "Deep Current")
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
    assert run("skills/score-cards/merge.py", "run", "zara", "Tundra").returncode == 0
    assert read("run/merged/zara/lands.md") == bare.replace("## Shape", """## Adds

| Card | Score | Role | Note | New | ~Price |
|---|---|---|---|---|---|
| Tundra | 8 | land | fits | - | - |

## Shape""")


def test_card_mode_patches_only_the_named_cards():
    scorers(scores={"Nonlands": {"Kelp Weaver": (7, 7, 6), "Sol Ring": (1, 1, 1)}})
    assert run("skills/score-cards/merge.py", "run", "zara", "Kelp Weaver").returncode == 0
    nonlands = read("run/merged/zara/nonlands.md")
    assert "| Kelp Weaver | 7 | engine | fits |" in nonlands and "| Sol Ring | 8 | ramp |" in nonlands


def test_card_mode_reads_a_file_without_the_role_column():
    nonlands, lands = without_roles("output/decks/zara/nonlands.md"), without_roles("output/decks/zara/lands.md")
    assert "Role" not in nonlands + lands and "| Misty Cove | 5 | Enters tapped for no gain |" in lands
    assert "| Card | Score | Note | New | ~Price |\n|---|---|---|---|---|\n| Deep Current | 7 | A card" in nonlands
    scorers(scores={"Nonlands": {"Kelp Weaver": (7, 7, 6)}})
    assert run("skills/score-cards/merge.py", "run", "zara", "Kelp Weaver").returncode == 0
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
Built 2025-01-01, last edited 2025-06-01.

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
    out = run("skills/score-cards/merge.py", "run", "zara")
    assert (out.returncode, out.stderr) == (1, "zara: not in the scorer files: Misty Cove, Sol Ring\n")
    out = run("skills/score-cards/merge.py", "run", "zara", "Kelp Weaver", "Pearl Diver")
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
