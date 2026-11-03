import copy
from pathlib import Path
from conftest import run, load, read

# each card's score from scorers A, B and C
SCORES = {
    "Nonlands": {"Zara, Tide Caller": (10, 10, 9), "Sol Ring": (8, 8, 8), "Tidal Insight": (7, 6, 8),
                 "Kelp Weaver": (6, 6, 6), "Brine Elemental": (2, 5, 6), "Coral Signet": (4, 4, 4),
                 "Wave Breaker": (3, 2, 3)},
    "Lands": {"Sunken Grotto": (7, 7, 7), "Island (4)": (6, 6, 6), "Misty Cove": (5, 4, 4)},
    "Adds": {"Deep Current": (8, 8, 7), "Tidepool Ruins": (6, 6, 6)},
}


def scorers(letters="ABC", scores=SCORES):
    """one scorer file per letter in run/, as the scorer agent shapes them"""
    Path("run").mkdir()
    for i, letter in enumerate(letters):
        text = f"# Zara, Tide Caller: fit scores ({letter})\n"
        for section, cards in scores.items():
            text += f"\n## {section}\n| Card | Score | Note |\n|---|---|---|\n"
            text += "".join(f"| {card} | {s[i]} | fits |\n" for card, s in cards.items())
        Path(f"run/zara-{letter}.md").write_text(text + "\n## Shape\nignored\n")


def test_parse_reads_every_section():
    scorers("A")
    got = load("score/merge.py").parse("run/zara-A.md")
    assert got["Island"] == ("Island (4)", 6, "fits", "lands")
    assert got["Deep Current"] == ("Deep Current", 8, "fits", "adds")
    assert got["Zara, Tide Caller"][3] == "nonlands"
    assert len(got) == 12


def test_key_and_copies():
    merge = load("score/merge.py")
    assert merge.key("4 Island (4)") == "Island"
    assert merge.key("Rising Tide // Tidal Flats") == "Rising Tide"
    assert merge.copies("Island (4)") == 4 and merge.copies("Island x 3") == 3 and merge.copies("Sol Ring") == 1


def test_merge_writes_the_file_pair():
    scorers()
    out = run("score/merge.py", "run", "zara")
    assert out.returncode == 0, out.stderr
    assert out.stderr.startswith("zara: 10: 1 / 8-9: 1 / 5-7: ") and out.stderr.endswith("3 scorers. 1 flagged\n")
    assert read("run/merged/zara/nonlands.md") == """# Zara, Tide Caller: nonlands

## Cards
| Card | Score | Note |
|---|---|---|
| Zara, Tide Caller | 10 | fits |
| Sol Ring | 8 | fits |
| Tidal Insight | 7 | fits |
| Kelp Weaver | 6 | fits |
| Brine Elemental | 5 | fits |
| Coral Signet | 4 | fits |
| Wave Breaker | 3 | fits |

## Adds
Built 2025-01-01, last edited 2025-06-01, bracket 2.

| Card | Score | Note | New | ~Price |
|---|---|---|---|---|
| Deep Current | 8 | fits | Yes | $1.50 |

## Cuts
| Card | Score | Why it underperforms here |
|---|---|---|
| Wave Breaker | 3 | Aggro body in a control deck |

## Shape
10: 1 / 8-9: 1 / 5-7: 3 / 4 or below: 2, mean 6.1 (by card copy), 3 scorers.
"""
    lands = read("run/merged/zara/lands.md")
    assert "| Island (4) | 6 | fits |" in lands
    assert "| Tidepool Ruins | 6 | fits | No | $0.40 |" in lands
    assert "| Misty Cove | 4 | Enters tapped for no gain |" in lands   # the cut takes this run's score
    assert lands.endswith("mean 5.8 (by card copy), 3 scorers.\n")
    flagged = read("run/zara-flagged.md")
    assert "## Brine Elemental\nScores A/B/C: [2, 5, 6]\n" in flagged and "Sol Ring" not in flagged


def test_one_scorer_stands_alone():
    scorers("A")
    out = run("score/merge.py", "run", "zara")
    assert out.stderr.endswith("1 scorer.\n")
    assert not Path("run/zara-flagged.md").exists()
    assert "| Brine Elemental | 2 | fits |" in read("run/merged/zara/nonlands.md")


def test_card_only_score_patches_the_deck_files():
    with open("output/decks/zara/list.txt", "a") as f: f.write("1 Deep Current\n")
    nonlands, lands = read("output/decks/zara/nonlands.md"), read("output/decks/zara/lands.md")
    scorers(scores={"Nonlands": {"Kelp Weaver": (7, 7, 6), "Deep Current": (8, 8, 5)}})
    out = run("score/merge.py", "run", "zara")
    assert out.returncode == 0, out.stderr
    assert out.stderr == "zara: 10: 1 / 8-9: 2 / 5-7: 9 / 4 or below: 2, mean 6.3 (by card copy), 3 scorers. 1 flagged\n"
    assert read("run/merged/zara/nonlands.md") == (nonlands
        .replace("| Kelp Weaver | 6 | Blocker that loots |\n", "")
        .replace("| Tidal Insight | 7 | Instant draw two |\n",
                 "| Deep Current | 8 | fits |\n| Tidal Insight | 7 | Instant draw two |\n| Kelp Weaver | 7 | fits |\n")
        .replace("| Deep Current | 7 | A card on every spell, stacks with Zara | Yes | $1.50 |\n", "")
        .replace("10: 1 / 8-9: 1 / 5-7: 3 / 4 or below: 2, mean 6.1", "10: 1 / 8-9: 2 / 5-7: 3 / 4 or below: 2, mean 6.5"))
    assert read("run/merged/zara/lands.md") == lands
    assert "## Deep Current\nScores A/B/C: [8, 8, 5]\n" in read("run/zara-flagged.md")


def test_card_only_score_puts_a_candidate_in_its_adds_table():
    nonlands, lands = read("output/decks/zara/nonlands.md"), read("output/decks/zara/lands.md")
    scorers(scores={"Nonlands": {"Kelp Weaver": (7, 7, 6), "Pearl Diver": (6, 6, 5), "Tundra": (8, 8, 7)},
                    "Adds": {"Deep Current": (8, 8, 5)}})
    out = run("score/merge.py", "run", "zara")
    assert out.returncode == 0, out.stderr
    assert out.stderr == "zara: 10: 1 / 8-9: 1 / 5-7: 9 / 4 or below: 2, mean 6.2 (by card copy), 3 scorers. 1 flagged\n"
    assert read("run/merged/zara/nonlands.md") == (nonlands
        .replace("| Kelp Weaver | 6 | Blocker that loots |\n", "| Kelp Weaver | 7 | fits |\n")
        .replace("| Deep Current | 7 | A card on every spell, stacks with Zara | Yes | $1.50 |\n",
                 "| Deep Current | 8 | fits | Yes | $1.50 |\n| Pearl Diver | 6 | fits | - | - |\n")
        .replace("mean 6.1", "mean 6.3"))
    assert read("run/merged/zara/lands.md") == lands.replace(
        "| Tidepool Ruins |", "| Tundra | 8 | fits | - | - |\n| Tidepool Ruins |")


def test_a_candidate_makes_the_adds_table_it_lacks():
    lands = read("output/decks/zara/lands.md")
    bare = lands[:lands.index("## Adds")] + lands[lands.index("## Shape"):]
    Path("output/decks/zara/lands.md").write_text(bare)
    scorers(scores={"Lands": {"Tundra": (8, 8, 7)}})
    assert run("score/merge.py", "run", "zara").returncode == 0
    assert read("run/merged/zara/lands.md") == bare.replace("## Shape", """## Adds

| Card | Score | Note | New | ~Price |
|---|---|---|---|---|
| Tundra | 8 | fits | - | - |

## Shape""")


def test_settings_defaults():
    settings = load("score/settings.py")
    Path("settings.json").unlink()
    defaults = copy.deepcopy(settings.DEFAULTS)
    assert settings.settings() == defaults
    Path("settings.json").write_text('{"scorers": 1, "quota": {"adds": 15}, "cart": {"finish": "nonfoil"}}')
    assert settings.settings() == {**defaults, "scorers": 1, "quota": {**defaults["quota"], "adds": 15},
                                   "cart": {**defaults["cart"], "finish": "nonfoil"}}
    assert settings.DEFAULTS == defaults


def test_settings_overrides():
    settings = load("score/settings.py")
    base, given, defaults = settings.settings(), read("settings.json"), copy.deepcopy(settings.DEFAULTS)
    got = settings.settings(["scorers=1", "quota.adds=15", "quota.cuts=[8, 12]", "cart.finish=nonfoil",
                             "model=claude-sonnet-5"])
    assert got == {**base, "scorers": 1, "model": "claude-sonnet-5", "quota": {"adds": 15, "lands": 5, "cuts": [8, 12]},
                   "cart": {**base["cart"], "finish": "nonfoil"}}
    assert settings.settings() == base and read("settings.json") == given and settings.DEFAULTS == defaults
    out = run("score/settings.py", "budget=50", "universes_beyond=false")
    assert out.returncode == 0 and '"budget": 50' in out.stdout and '"universes_beyond": false' in out.stdout
