import copy, json
from urllib.error import HTTPError
from pathlib import Path
import pytest
from conftest import run, read
import facts, fetch_brackets, fetch_syntax, merge, merge_rankings, project, settings, tables

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


# each deck's Win, Development, Setup, Rebuild and Flow from rankers A to E; zara's Salt is 4, kor's 3, and both decks'
# Interaction 1, their cards untagged
JUDGED = {"zara": {"A": [6, 5, 3, 4, 5], "B": [7, 6, 4, 5, 5], "C": [3, 4, 4, 3, 3]},
          "kor": {"A": [5, 6, 3, 3, 3], "B": [8, 7, 4, 4, 4], "C": [8, 7, 4, 4, 4]}}
OWN = dict(zip("ABCDE", ["3", "4", "2", "3, top", "3"]))  # each ranker's Bracket
JUDGMENTS_RULE = "|---|---|---|---|---|---|---|---|"


def flat(speed, resilience):
    """a ranker's JUDGED values with both Speed axes at speed and all three Resilience axes at resilience"""
    return [speed] * 2 + [resilience] * 3
UNTAGGED = "1 | 0 answers, 0 instant; no/no/no | -"  # an untagged deck's Interaction Ledger cells past the criterion


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
    return [f"| {slug} | {a} | 5 | - | cards {x} |" for a in merge_rankings.JUDGED]


def rankers(judged=JUDGED, letters="ABC", order=None):
    """one run/rankings-<letter>.md per letter in the ranker agent's shape, its decks in order[letter] or strongest
    first by its own values; makes the decks first"""
    if not Path("run").exists(): decks()
    for x in letters:
        slugs = (order or {}).get(x) or sorted(judged, key=lambda d: -sum(judged[d][x]))
        rows = "".join(f"| {d} | {' | '.join(map(str, judged[d][x]))} | {OWN[x]} | why {x} |\n"
                       for d in slugs)
        books = "".join(f"{l}\n" for d in slugs for l in ledger(d, x))
        Path(f"run/rankings-{x}.md").write_text(f"# Judgments ({x})\n\n{merge_rankings.JUDGMENTS}\n{JUDGMENTS_RULE}\n"
                                                f"{rows}\n## Ledger\n\n| Deck | Criterion | Value | Count | Cards |\n"
                                                f"|---|---|---|---|---|\n{books}")


def ranked():
    """run/rankings.md as {slug: {column: cell}}, its Rankings, Criteria, Speed and Resilience columns by criterion, its
    decks in order"""
    secs = dict(tables.split(read("run/rankings.md")))
    heads = lambda h: [c.strip().removesuffix(" /5") or "Moxfield" for c in h.strip("|").split("|")]
    by = lambda head, sec: {r[0]: dict(zip(heads(head), r)) for r in tables.cells(secs[sec])}
    crit, speed, resil = by(merge_rankings.CRITERIA, "## Criteria"), by(merge_rankings.SPEED, "## Speed"), \
        by(merge_rankings.RESILIENCE, "## Resilience")
    return {r[1].split("decks/")[1].rstrip("/)"):
            crit[r[0]] | speed[r[0]] | resil[r[0]] | dict(zip(heads(merge_rankings.RANKINGS), r))
            for r in tables.cells(secs[None])}


def merges(*stderr):
    """ranked() after a merge that succeeds printing these lines"""
    out = run("skills/score/merge_rankings.py", "run")
    assert (out.returncode, out.stderr) == (0, "".join(f"{l}\n" for l in stderr))
    return ranked()


def test_merge_rankings_takes_the_mean_of_three_rankers_and_computes_the_rest():
    rankers()
    merges("zara: split Win 6/7/3")
    # zara's Win 16 / 3 = 5.3 and Development 15 / 3 = 5.0, Speed their mean 5.15, 5.2; its axes 3.7, 4.0 and 4.3,
    # Resilience their mean 4.0; with Interaction 1 and Salt 4 its Score is (4.2 / 8 + 3 / 4 + 0 / 8 + 3 / 8) / 4 * 100
    # = 41.25; its own Scores 42.2 (5.5, 4.0), 49.7 (6.5, 4.7) and 31.6 (3.5, 3.3) make A the median; kor's Win 7.0 and
    # Development 6.7, Speed 6.85, 6.9, and axes 3.7, with Salt 3 (5.9 / 8 + 2.7 / 4 + 0 + 2 / 8) / 4 * 100 = 41.5625,
    # its own 32.8, 45.3 and 45.3 make B the median
    assert read("run/rankings.md") == f"""# Rankings

{merge_rankings.RANKINGS}
|---|---|---|---|---|---|---|---|
| 1 | [Kor Skyfisher](output/decks/kor/) | W | 4 | 41.6 | none | why B | [Moxfield](https://moxfield.com/decks/k1) |
| 2 | [Zara, Tide Caller](output/decks/zara/) | U | 3 | 41.3 | none | why A | [Moxfield](https://moxfield.com/decks/z1) |

## Criteria

| # | Commander | Speed | Resilience /5 | Interaction | Salt |
|---|---|---|---|---|---|
| 1 | Kor Skyfisher | 6.9 | 3.7 | 1.0 | 3.0 |
| 2 | Zara, Tide Caller | 5.2 | 4.0 | 1.0 | 4.0 |

## Speed

| # | Commander | Win | Development |
|---|---|---|---|
| 1 | Kor Skyfisher | 7.0 | 6.7 |
| 2 | Zara, Tide Caller | 5.3 | 5.0 |

## Resilience

| # | Commander | Setup /5 | Rebuild /5 | Flow /5 |
|---|---|---|---|---|
| 1 | Kor Skyfisher | 3.7 | 3.7 | 3.7 |
| 2 | Zara, Tide Caller | 3.7 | 4.0 | 4.3 |

## Ledger

{merge_rankings.LEDGER}
|---|---|---|---|---|
| Kor Skyfisher | Win | 5 | - | cards B |
| Kor Skyfisher | Development | 5 | - | cards B |
| Kor Skyfisher | Setup | 5 | - | cards B |
| Kor Skyfisher | Rebuild | 5 | - | cards B |
| Kor Skyfisher | Flow | 5 | - | cards B |
| Kor Skyfisher | Interaction | {UNTAGGED} |
| Kor Skyfisher | Salt | 3 | mean 0.45 over 1 cards | - |
| Zara, Tide Caller | Win | 5 | - | cards A |
| Zara, Tide Caller | Development | 5 | - | cards A |
| Zara, Tide Caller | Setup | 5 | - | cards A |
| Zara, Tide Caller | Rebuild | 5 | - | cards A |
| Zara, Tide Caller | Flow | 5 | - | cards A |
| Zara, Tide Caller | Interaction | {UNTAGGED} |
| Zara, Tide Caller | Salt | 4 | mean 0.53 over 1 cards | - |
"""


def counted(answers, instant, wipes=0, counters=0, creature=0, noncreature=0):
    return {"Answers": answers, "Instant-speed answers": instant, "Wipes": wipes, "Counters": counters,
            "Creature removal": creature, "Noncreature removal": noncreature}


@pytest.mark.parametrize("counts, level, count", [
    (counted(15, 10, 0, 1, 1, 1), 9, "15 answers, 10 instant; yes/yes/yes"),  # 9 needs no wipe
    (counted(20, 9, 1, 1, 1, 1), 7, "20 answers, 9 instant; yes/yes/yes"),  # 9 needs 10 instant
    (counted(15, 10, 1, 0, 1, 1), 7, "15 answers, 10 instant; no/yes/yes"),  # 9 needs counters, 7 does not
    (counted(11, 7, 1, 0, 1, 1), 7, "11 answers, 7 instant; no/yes/yes"),
    (counted(14, 10, 0, 1, 1, 1), 5, "14 answers, 10 instant; yes/yes/yes"),  # 7 needs a wipe
    (counted(14, 10, 1, 1, 1, 0), 5, "14 answers, 10 instant; yes/yes/no"),  # 7 needs noncreature removal
    (counted(11, 5, 1, 1, 1, 1), 5, "11 answers, 5 instant; yes/yes/yes"),  # fewer than half instant
    (counted(7, 0), 5, "7 answers, 0 instant; no/no/no"),
    (counted(6, 6, 1, 1, 1, 1), 3, "6 answers, 6 instant; yes/yes/yes"),
    (counted(3, 0), 3, "3 answers, 0 instant; no/no/no"),
    (counted(2, 2, 1, 1, 0, 0), 1, "2 answers, 2 instant; yes/no/no"),
    (counted(0, 0), 1, "0 answers, 0 instant; no/no/no"),
])
def test_interaction_is_the_highest_row_of_its_table_the_counts_meet(counts, level, count):
    assert merge_rankings.interaction(counts) == (level, count)


def test_the_merged_ledgers_interaction_row_carries_the_answers_cards_and_the_coverage():
    decks()
    oracle = json.loads(read("output/data/oracle.json"))
    tags = {"Tidal Insight": ["counterspell"], "Wave Breaker": ["removal", "removal-creature"],
            "Brine Elemental": ["removal", "sweeper"]}
    for name, t in tags.items(): oracle["cards"][name]["tags"] = t
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    facts.counts("run", "zara")
    rankers()
    assert merges("zara: split Win 6/7/3")["zara"]["Interaction"] == "3.0"
    assert "| Zara, Tide Caller | Interaction | 3 | 3 answers, 1 instant; yes/yes/no | " \
           "Brine Elemental; Tidal Insight; Wave Breaker |\n" in read("run/rankings.md")


def test_merge_rankings_stops_on_a_counts_file_without_a_row_it_reads():
    rankers()
    counts = Path("run/zara-counts.md")
    counts.write_text("".join(l for l in counts.read_text().splitlines(True) if not l.startswith("| Creature removal |")))
    out = run("skills/score/merge_rankings.py", "run")
    assert (out.returncode, out.stderr) == (1, "zara-counts.md: no Creature removal row, rerun facts.py\n")


def test_merge_rankings_takes_the_middle_three_of_five_and_the_median_rankers_cells():
    # each Speed axis 1 5 6 7 9 keeps 5 6 7, each Resilience axis 2 2 3 5 5 keeps 2 3 5; own Scores 15.6 59.4 28.1 37.5
    # 53.1 make D the median
    five = {"zara": {"A": flat(1, 2), "B": flat(9, 5), "C": flat(5, 2), "D": flat(6, 3), "E": flat(7, 5)},
            "kor": {x: flat(5, 5) for x in "ABCDE"}}
    rankers(five, "ABCDE")
    got = merges("zara: split Win 1/9/5/6/7, Development 1/9/5/6/7")["zara"]
    # (5.0 / 8 + 2.3 / 4 + 0 / 8 + 3 / 8) / 4 * 100 = 39.375, its Score 39.4
    assert [got[c] for c in ("Speed", "Resilience", "Interaction", "Salt", "Score", "Bracket", "Why")] == \
        ["6.0", "3.3", "1.0", "4.0", "39.4", "3, top", "why D"]
    assert "| Zara, Tide Caller | Setup | 5 | - | cards D |" in read("run/rankings.md")


def test_merge_rankings_rounds_a_mean_of_two_or_four_half_up():
    rankers({"zara": {"A": flat(5, 4), "B": flat(6, 5)}, "kor": {x: flat(5, 5) for x in "AB"}}, "AB")
    assert [merges()["zara"][c] for c in ("Speed", "Setup", "Resilience")] == ["5.5", "4.5", "4.5"]
    rankers({"zara": {"A": flat(5, 5), "B": flat(5, 5), "C": flat(5, 5), "D": flat(6, 5)},
             "kor": {x: flat(5, 5) for x in "ABCD"}}, "ABCD")
    assert merges()["zara"]["Speed"] == "5.3"  # 21 / 4 = 5.25


def test_speed_and_resilience_are_the_means_of_their_merged_axes_and_the_score_normalises_each_from_its_range():
    rankers({"zara": {"A": [5, 3, 5, 3, 1], "B": [6, 3, 4, 4, 2]}, "kor": {x: flat(5, 5) for x in "AB"}}, "AB")
    got = merges()["zara"]
    # Win 5.5 and Development 3.0: Speed 8.5 / 2 = 4.25; axes 4.5, 3.5 and 1.5: Resilience 9.5 / 3 = 3.17; Speed
    # (4.3 - 1) / 8 = 0.4125, Resilience (3.2 - 1) / 4 = 0.55, Interaction 0 / 8 and Salt 3 / 8 = 0.375:
    # (0.4125 + 0.55 + 0 + 0.375) / 4 * 100 = 33.4375
    assert [got[c] for c in ("Win", "Development", "Speed", "Resilience", "Interaction", "Salt", "Setup", "Rebuild",
                             "Flow", "Score")] == \
        ["5.5", "3.0", "4.3", "3.2", "1.0", "4.0", "4.5", "3.5", "1.5", "33.4"]


def test_merge_rankings_rounds_a_score_ending_in_5_up():
    # Speed 5.0 and every axis 4 5, 4.5 each, Interaction 1 and Salt 4: (4 / 8 + 3.5 / 4 + 0 + 3 / 8) / 4 * 100 = 43.75
    rankers({"zara": {"A": flat(5, 4), "B": flat(5, 5)}, "kor": {x: flat(5, 5) for x in "AB"}}, "AB")
    assert merges()["zara"]["Score"] == "43.8"


def test_merge_rankings_breaks_a_tie_by_mean_place_then_by_slug():
    same = {"zara": {x: flat(5, 5) for x in "ABC"}, "kor": {x: flat(5, 5) for x in "ABC"}}
    decks({"Zara, Tide Caller": 0.45, "Kor Skyfisher": 0.45})
    rankers(same, order={"A": ["zara", "kor"], "B": ["zara", "kor"], "C": ["kor", "zara"]})
    assert list(merges()) == ["zara", "kor"]
    for x in "ABC": Path(f"run/rankings-{x}.md").unlink()
    rankers(same, "AB", order={"A": ["zara", "kor"], "B": ["kor", "zara"]})
    assert list(merges()) == ["kor", "zara"]


def test_one_ranker_goes_through_the_merge():
    rankers(letters="B")
    got = merges()
    # zara Speed 13 / 2 = 6.5, Resilience 14 / 3 = 4.7, 1 and Salt 4: (5.5 / 8 + 3.7 / 4 + 0 + 3 / 8) / 4 * 100
    # = 49.6875; kor 7.5, 4, 1 and Salt 3: (6.5 / 8 + 3 / 4 + 0 + 2 / 8) / 4 * 100 = 45.3125
    assert [(d, got[d]["Score"], got[d]["Speed"], got[d]["Why"]) for d in got] == \
        [("zara", "49.7", "6.5", "why B"), ("kor", "45.3", "7.5", "why B")]


@pytest.mark.parametrize("change, faults", [
    (lambda t: t.replace("| kor |", "| ghost |"), ["kor: missing", "ghost: not a deck of the run"]),
    (lambda t: t + "| ghost | 5 | 5 | 5 | 5 | 5 | 3 | why |\n", ["ghost: not a deck of the run"]),
    (lambda t: t.replace("| zara | 6 |", "| zara | 10 |"), ["zara: Win 10 is not a whole number from 1 to 9"]),
    (lambda t: t.replace("| zara | 6 | 5 | 3 |", "| zara | 6 | 5 | 6 |"),
     ["zara: Setup 6 is not a whole number from 1 to 5"]),
    (lambda t: t.replace("| zara | 6 | 5 | 3 | 4 |", "| zara | 6 | 5 | 3 | 3.5 |"),
     ["zara: Rebuild 3.5 is not a whole number from 1 to 5"]),
    (lambda t: t.replace("| 3 | why A |", "| 3 top | why A |", 1),
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
    got = merges("zara: split Win 6/7/3")
    assert got["kor"]["Moxfield"] == "-" and got["zara"]["Moxfield"] == "[Moxfield](https://moxfield.com/decks/z1)"
    assert got["kor"]["Game Changers"] == got["zara"]["Game Changers"] == "Sol Ring"
    assert got["zara"]["Colours"] == "WUG"
    Path("moxfield.json").unlink()
    assert merges("zara: split Win 6/7/3")["zara"]["Moxfield"] == "-"


def recomputed():
    """the merged rankings.md beside output/, the run's own copy and ranker files gone, then a recompute"""
    rankers()
    merges("zara: split Win 6/7/3")
    Path("rankings.md").write_text(read("run/rankings.md"))
    for p in Path("run").glob("rankings*.md"): p.unlink()
    return run("skills/score/merge_rankings.py", "--recompute", "run")


def test_recompute_on_an_unchanged_project_reproduces_rankings_md():
    out = recomputed()
    assert (out.returncode, out.stderr) == (0, "")
    assert read("run/rankings.md") == read("rankings.md")


def test_recompute_after_a_salt_change_moves_only_that_decks_salt_score_and_place():
    assert recomputed().returncode == 0
    before = ranked()
    oracle = json.loads(read("output/data/oracle.json"))
    oracle["cards"]["Zara, Tide Caller"]["salt"] = 0.9
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    for slug in ("zara", "kor"): facts.counts("run", slug)
    assert run("skills/score/merge_rankings.py", "--recompute", "run").returncode == 0
    after = ranked()
    # zara's Salt 9: (4.2 / 8 + 3 / 4 + 0 + 8 / 8) / 4 * 100 = 56.875, its Score 56.9 above kor's 41.6
    assert list(after) == ["zara", "kor"]
    assert after["kor"] == before["kor"] | {"#": "2"}
    assert after["zara"] == before["zara"] | {"#": "1", "Salt": "9.0", "Score": "56.9"}
    assert "| Zara, Tide Caller | Salt | 9 | mean 0.90 over 1 cards | - |" in read("run/rankings.md")


def test_recompute_reads_both_axis_tables_and_computes_speed_and_resilience_from_them():
    assert recomputed().returncode == 0
    Path("rankings.md").write_text(read("rankings.md").replace("| Zara, Tide Caller | 5.3 | 5.0 |",
                                                               "| Zara, Tide Caller | 9.0 | 5.0 |")
                                   .replace("| Zara, Tide Caller | 3.7 | 4.0 | 4.3 |",
                                            "| Zara, Tide Caller | 5.0 | 4.0 | 4.3 |"))
    assert run("skills/score/merge_rankings.py", "--recompute", "run").returncode == 0
    # Win 9.0 and Development 5.0: Speed 7.0; axes 5.0, 4.0 and 4.3: Resilience 13.3 / 3 = 4.43;
    # (6 / 8 + 3.4 / 4 + 0 + 3 / 8) / 4 * 100 = 49.375
    got = ranked()["zara"]
    assert [got[c] for c in ("Win", "Speed", "Setup", "Resilience", "Score")] == ["9.0", "7.0", "5.0", "4.4", "49.4"]


def test_recompute_stops_on_a_rankings_md_whose_axes_are_not_on_1_to_5():
    assert recomputed().returncode == 0
    Path("rankings.md").write_text(read("rankings.md").replace(" /5", ""))
    out = run("skills/score/merge_rankings.py", "--recompute", "run")
    assert (out.returncode, out.stderr) == (1, "rankings.md axes are not on 1 to 5, rank the decks\n")


@pytest.mark.parametrize("name", ["Speed", "Resilience"])
def test_recompute_stops_on_a_rankings_md_without_an_axis_table(name):
    assert recomputed().returncode == 0
    secs = [s for s in tables.split(read("rankings.md")) if s[0] != f"## {name}"]
    Path("rankings.md").write_text(tables.join(secs))
    out = run("skills/score/merge_rankings.py", "--recompute", "run")
    assert (out.returncode, out.stderr) == (1, f"rankings.md has no {name} table, rank the decks\n")


def test_recompute_stops_on_a_deck_rankings_md_lacks():
    assert recomputed().returncode == 0
    Path("run/ghost-counts.md").write_text(read("run/zara-counts.md"))
    out = run("skills/score/merge_rankings.py", "--recompute", "run")
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
