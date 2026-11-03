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


def scorers(letters="ABC"):
    """one scorer file per letter in run/, as the scorer agent shapes them"""
    Path("run").mkdir()
    for i, letter in enumerate(letters):
        text = f"# Zara, Tide Caller: fit scores ({letter})\n"
        for section, cards in SCORES.items():
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


def test_settings_from_the_file():
    assert load("score/settings.py").settings() == {"scorers": 3, "model": "claude-opus-5-5", "budget": 20}


def test_settings_defaults():
    settings = load("score/settings.py")
    Path("settings.json").unlink()
    assert settings.settings() == settings.DEFAULTS == {"scorers": 3, "model": "claude-opus-5-5", "budget": None}
    Path("settings.json").write_text('{"scorers": 1}')
    assert settings.settings() == {"scorers": 1, "model": "claude-opus-5-5", "budget": None}
