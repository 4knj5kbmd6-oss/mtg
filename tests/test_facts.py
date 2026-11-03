import json, sys
from pathlib import Path
from urllib.error import URLError
import pytest
from conftest import ROOT, run, read
import combos as script, facts, mana
from net import Failed

SAVED = ROOT / "tests" / "spellbook"  # Spellbook's answers for two real decks, trimmed to a few combos
SLUG = {"The Beamtown Bullies": "beamtown", "Braids, Arisen Nightmare": "braids"}  # each saved deck by its commander


def deck(slug, commander, cards, adds=()):
    """a deck folder with this list and these cards in its nonlands.md Adds table"""
    folder = Path(f"output/decks/{slug}"); folder.mkdir()
    (folder / "list.txt").write_text(f"1 {commander}\n\n" + "".join(f"{n} {c}\n" for c, n in cards.items()))
    (folder / "nonlands.md").write_text("# Deck: nonlands\n\n## Adds\n| Card | Score | Note | New | ~Price |\n"
                                        "|---|---|---|---|---|\n" + "".join(f"| {a} | - | fits | No | $1 |\n" for a in adds))


@pytest.fixture
def combos(monkeypatch):
    """combos.py with Spellbook answering from the saved files of the deck whose commander is posted"""
    module, posted = script, []
    def get(url, body):
        posted.append((url, body))
        return (SAVED / f"{SLUG[body['commanders'][0]['card']]}-{url.rstrip('/').rsplit('/', 1)[1]}.json").read_bytes()
    monkeypatch.setattr(module, "get", get)
    module.posted = posted
    Path("run").mkdir()
    return module


def write(combos, slug):
    combos.write("run", slug)
    return read(f"run/{slug}-combos.md")


def test_combos_one_card_away_list_only_missing_cards_in_the_adds(combos, monkeypatch, capsys):
    deck("beamtown", "The Beamtown Bullies", {"Bloom Tender": 1, "Seeker of Skybreak": 1, "Bronze Bombshell": 1,
                                              "Not A Card": 1},
         adds=["Illusionist's Bracers", "Thornbite Staff"])
    assert write(combos, "beamtown") == """# beamtown: Commander Spellbook combos

## Included
| Cards | Result | Two-card |
|---|---|---|

## Almost included
| Missing | Present | Result |
|---|---|---|
| Illusionist's Bracers | Seeker of Skybreak | Infinite mana creatures you control can produce, Infinite untap of creatures you control |
| Thornbite Staff | The Beamtown Bullies + Bronze Bombshell | Infinite damage |

## Flagged cards
| Card | Flag |
|---|---|
"""
    assert [u for u, _ in combos.posted] == ["https://backend.commanderspellbook.com/find-my-combos/",
                                             "https://backend.commanderspellbook.com/estimate-bracket/"]
    assert combos.posted[0][1] == {"commanders": [{"card": "The Beamtown Bullies"}], "main": [
        {"card": "Bloom Tender", "quantity": 1}, {"card": "Seeker of Skybreak", "quantity": 1},
        {"card": "Bronze Bombshell", "quantity": 1}, {"card": "Not A Card", "quantity": 1}]}
    assert capsys.readouterr().out == "beamtown: not on Commander Spellbook: Not A Card\n"


def test_included_combos_carry_spellbooks_two_card_mark_and_flags(combos, monkeypatch):
    deck("braids", "Braids, Arisen Nightmare", {"Ashnod's Altar": 1, "Gravecrawler": 1, "Phyrexian Altar": 1,
                                                "Pitiless Plunderer": 1, "Reassembling Skeleton": 1})
    bracket = json.loads((SAVED / "braids-estimate-bracket.json").read_text())
    bracket["combos"][0]["arguablyTwoCard"] = bracket["combos"][1]["definitelyTwoCard"] = True
    bracket["cards"][0]["massLandDenial"] = bracket["cards"][0]["extraTurn"] = True
    saved = combos.get
    monkeypatch.setattr(combos, "get", lambda url, body: json.dumps(bracket).encode() if "bracket" in url else saved(url, body))
    text = write(combos, "braids")
    assert text.split("## Almost included")[0] == """# braids: Commander Spellbook combos

## Included
| Cards | Result | Two-card |
|---|---|---|
| Gravecrawler + Phyrexian Altar | Infinite death triggers, Infinite creature ETB, Infinite creature LTB, Infinite creature sacrifice triggers, Infinite storm count | definite |
| Pitiless Plunderer + Ashnod's Altar + Reassembling Skeleton | Infinite colorless mana, Infinite death triggers, Infinite creature ETB, Infinite creature LTB, Infinite creature sacrifice triggers | arguable |

"""
    assert text.endswith("## Flagged cards\n| Card | Flag |\n|---|---|\n| Ashnod's Altar | mass land denial |\n"
                         "| Ashnod's Altar | extra turns |\n")


@pytest.mark.parametrize("answer, url", [
    (URLError("down"), "find-my-combos"),
    (Failed("https://backend.commanderspellbook.com/find-my-combos/: HTTP 503"), "find-my-combos"),
    (b"<title>Just a moment...</title>", "estimate-bracket"),
])
def test_no_answer_from_spellbook_names_the_url_and_writes_nothing(combos, monkeypatch, capsys, answer, url):
    deck("beamtown", "The Beamtown Bullies", {"Seeker of Skybreak": 1})
    def get(u, body):
        if url not in u: return (SAVED / "beamtown-find-my-combos.json").read_bytes()
        if isinstance(answer, BaseException): raise answer
        return answer
    monkeypatch.setattr(combos, "get", get)
    combos.write("run", "beamtown")
    assert capsys.readouterr().out == f"Commander Spellbook unreachable: https://backend.commanderspellbook.com/{url}/\n"
    assert not Path("run/beamtown-combos.md").exists()


ANY = ["B", "G", "R", "U", "W"]
FETCH = "{{T}}, Pay 1 life, Sacrifice {0}: Search your library for {1} card, put it onto the battlefield, then shuffle."
WILD = "{{T}}, Sacrifice {0}: Search your library for a basic land card, put it onto the battlefield tapped, then shuffle."
CARDS = {  # name: (type, cost, mana value, produced_mana, oracle text)
    "Lazav, Dimir Mastermind": ("Legendary Creature — Shapeshifter", "{U}{U}{B}{B}", 4, None, "Hexproof"),
    "Polluted Delta": ("Land", None, 0, None, FETCH.format("Polluted Delta", "an Island or Swamp")),
    "Flooded Strand": ("Land", None, 0, None, FETCH.format("Flooded Strand", "a Plains or Island")),
    "Tidal Path": ("Land", None, 0, None, FETCH.format("Tidal Path", "an Island")),
    "Fabled Passage": ("Land", None, 0, None, WILD.format("Fabled Passage") + " Then if you control four or more lands, untap that land."),
    "Evolving Wilds": ("Land", None, 0, None, WILD.format("Evolving Wilds")),
    "Command Tower": ("Land", None, 0, ANY, "{T}: Add one mana of any color in your commander's color identity."),
    "Island": ("Basic Land — Island", None, 0, ["U"], "({T}: Add {U}.)"),
    "Swamp": ("Basic Land — Swamp", None, 0, ["B"], "({T}: Add {B}.)"),
    "Mox Opal": ("Legendary Artifact", "{0}", 0, ANY, "Metalcraft — {T}: Add one mana of any color."),
    "Sol Ring": ("Artifact", "{1}", 1, ["C"], "{T}: Add {C}{C}."),
    "Dark Ritual": ("Instant", "{B}", 1, ["B"], "Add {B}{B}{B}."),
    "Arcane Signet": ("Artifact", "{2}", 2, ANY, "{T}: Add one mana of any color in your commander's color identity."),
    "Counterspell": ("Instant", "{U}{U}", 2, None, "Counter target spell."),
    "Phyrexian Arena": ("Enchantment", "{1}{B}{B}", 3, None, "At the beginning of your upkeep, you draw a card and you lose 1 life."),
    "Massacre Wurm": ("Creature — Phyrexian Wurm", "{3}{B}{B}{B}", 6, None, "When this creature enters, creatures your opponents control get -2/-2 until end of turn."),
    "Sphinx of the Final Word": ("Creature — Sphinx", "{5}{U}{U}", 7, None, "This spell can't be countered."),
}


def test_mana_counts_fetch_lands_by_the_types_they_find(capsys):
    oracle = {n: {"name": n, "type_line": t, "cmc": v, "oracle_text": o, "color_identity": ["B", "U"] if n.startswith("Lazav") else [],
                  **({"mana_cost": c} if c else {}), **({"produced_mana": p} if p else {})} for n, (t, c, v, p, o) in CARDS.items()}
    Path("output/data/oracle.json").write_text(json.dumps({"cards": oracle}))
    deck("lazav", "Lazav, Dimir Mastermind", {**{n: 1 for n in list(CARDS)[1:]}, "Island": 4, "Swamp": 3, "Mystery Card": 1})
    Path("run").mkdir()
    mana.write("run", "lazav")
    assert capsys.readouterr().out == "lazav: not in oracle.json: Mystery Card\n"
    # 13 lands and 8 nonlands in the 21 drawn from; 9 nonlands with the commander, 26 mana value between them
    # U: Delta, Strand, Path, Passage, Wilds, Tower, 4 Island; Mox, Signet; Lazav 2, Counterspell 2, Sphinx 2
    # B: Delta, Passage, Wilds, Tower, 3 Swamp; Mox, Ritual, Signet; Lazav 2, Ritual 1, Arena 2, Wurm 3
    assert read("run/lazav-mana.md") == """# lazav: mana

## Curve
| Lands | Nonlands | Mean mana value | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7+ |
|---|---|---|---|---|---|---|---|---|---|---|
| 13 | 9 | 2.9 | 1 | 2 | 2 | 1 | 1 | 0 | 1 | 1 |

## Opening seven
| 2 lands | 3 lands | 4 lands |
|---|---|---|
| 4% | 17% | 34% |

## Colours
| Colour | Land sources | Nonland sources | Pips | Cards with 2+ pips | Lowest mana value of those |
|---|---|---|---|---|---|
| U | 10 | 2 | 6 | 3 | 2 |
| B | 7 | 3 | 8 | 3 | 3 |
"""


def test_mana_odds_are_unknown_with_fewer_than_seven_known_cards(capsys):
    oracle = {"Sol Ring": {"name": "Sol Ring", "type_line": "Artifact", "cmc": 1, "mana_cost": "{1}", "produced_mana": ["C"]},
              "Island": {"name": "Island", "type_line": "Basic Land — Island", "cmc": 0, "produced_mana": ["U"]},
              "Zara, Tide Caller": {"name": "Zara, Tide Caller", "type_line": "Legendary Creature", "cmc": 2,
                                    "mana_cost": "{1}{U}", "color_identity": ["U"]}}
    Path("output/data/oracle.json").write_text(json.dumps({"cards": oracle}))
    deck("tiny", "Zara, Tide Caller", {"Sol Ring": 1, "Island": 5, "Mystery Card": 3})
    Path("run").mkdir()
    mana.write("run", "tiny")
    assert capsys.readouterr().out == "tiny: not in oracle.json: Mystery Card\n"
    assert read("run/tiny-mana.md") == """# tiny: mana

## Curve
| Lands | Nonlands | Mean mana value | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7+ |
|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 2 | 1.5 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |

## Opening seven
| 2 lands | 3 lands | 4 lands |
|---|---|---|
| unknown | unknown | unknown |

## Colours
| Colour | Land sources | Nonland sources | Pips | Cards with 2+ pips | Lowest mana value of those |
|---|---|---|---|---|---|
| U | 5 | 0 | 1 | 0 | - |
"""


def test_facts_writes_both_files_per_deck(combos, monkeypatch):
    deck("beamtown", "The Beamtown Bullies", {"Sol Ring": 1, "Island": 7})
    deck("braids", "Braids, Arisen Nightmare", {"Sol Ring": 1, "Island": 7})
    monkeypatch.setattr(sys, "argv", ["facts.py", "run", "beamtown", "braids"])
    facts.main()
    assert sorted(p.name for p in Path("run").iterdir()) == ["beamtown-combos.md", "beamtown-mana.md",
                                                             "braids-combos.md", "braids-mana.md"]
