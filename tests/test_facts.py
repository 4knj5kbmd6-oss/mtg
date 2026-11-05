import gzip, json, os, sys, time
from pathlib import Path
from urllib.error import URLError
import pytest
from conftest import ROOT, run, read
import combos as script, facts, karsten, mana
from net import Failed

SAVED = ROOT / "tests" / "spellbook"  # Spellbook's estimate-bracket answers for two real decks and its variants file, trimmed
SLUG = {"The Beamtown Bullies": "beamtown", "Braids, Arisen Nightmare": "braids"}  # each saved deck by its commander
COLOURS = {"The Beamtown Bullies": ["B", "G", "R"], "Braids, Arisen Nightmare": ["B"]}
BULK = "https://json.commanderspellbook.com/variants.json.gz"
BRACKET = "https://backend.commanderspellbook.com/estimate-bracket/"
CACHED = Path("output/data/variants.json.gz")


def deck(slug, commander, cards, adds=()):
    """a deck folder with this list and these cards in its nonlands.md Adds table; a saved deck's commander goes
    into oracle.json with its colours"""
    folder = Path(f"output/decks/{slug}"); folder.mkdir()
    (folder / "list.txt").write_text(f"1 {commander}\n\n" + "".join(f"{n} {c}\n" for c, n in cards.items()))
    (folder / "nonlands.md").write_text("# Deck: nonlands\n\n## Adds\n| Card | Score | Note | New | ~Price |\n"
                                        "|---|---|---|---|---|\n" + "".join(f"| {a} | - | fits | No | $1 |\n" for a in adds))
    if commander in COLOURS:
        oracle = json.loads(read("output/data/oracle.json"))
        oracle["cards"][commander] = {"name": commander, "color_identity": COLOURS[commander]}
        Path("output/data/oracle.json").write_text(json.dumps(oracle))


def answering(combos, monkeypatch, url, answer):
    """Spellbook answering url with answer, raised when it is an error, and everything else as saved"""
    saved = combos.get
    def get(u, body=None):
        if u != url: return saved(u, body)
        if isinstance(answer, BaseException): raise answer
        return answer
    monkeypatch.setattr(combos, "get", get)


@pytest.fixture
def combos(monkeypatch):
    """combos.py with Spellbook sending the saved variants file, gzipped, and answering estimate-bracket with the
    saved answer of the deck whose commander is posted"""
    module, asked = script, []
    def get(url, body=None):
        asked.append((url, body))
        if url == BULK: return gzip.compress((SAVED / "variants.json").read_bytes())
        return (SAVED / f"{SLUG[body['commanders'][0]['card']]}-estimate-bracket.json").read_bytes()
    monkeypatch.setattr(module, "get", get)
    module.variants.cache_clear()
    module.asked = asked
    Path("run").mkdir()
    yield module
    module.variants.cache_clear()


def write(combos, slug):
    combos.write("run", slug)
    return read(f"run/{slug}-combos.md")


def test_combos_one_card_away_list_only_missing_cards_in_the_adds(combos, capsys):
    deck("beamtown", "The Beamtown Bullies", {"Bloom Tender": 1, "Seeker of Skybreak": 1, "Bronze Bombshell": 1,
                                              "Not A Card": 1},
         adds=["Illusionist's Bracers", "Thornbite Staff"])
    assert write(combos, "beamtown") == """# beamtown: combos from commanderspellbook.com

## Included
| Cards | Result | Two-card | Bracket tag | Salt |
|---|---|---|---|---|

## Almost included
| Missing | Present | Result | Bracket tag | Salt |
|---|---|---|---|---|
| Illusionist's Bracers | Seeker of Skybreak | Infinite mana creatures you control can produce, Infinite untap of creatures you control | Spicy | - |
| Thornbite Staff | The Beamtown Bullies + Bronze Bombshell | Infinite damage | Exhibition | - |

## Flagged cards
| Card | Flag |
|---|---|
"""
    assert [u for u, _ in combos.asked] == [BULK, BRACKET]
    assert combos.asked[1][1] == {"commanders": [{"card": "The Beamtown Bullies"}], "main": [
        {"card": "Bloom Tender", "quantity": 1}, {"card": "Seeker of Skybreak", "quantity": 1},
        {"card": "Bronze Bombshell", "quantity": 1}, {"card": "Not A Card", "quantity": 1}]}
    assert gzip.decompress(CACHED.read_bytes()) == (SAVED / "variants.json").read_bytes()
    assert capsys.readouterr().out == "beamtown: not on Commander Spellbook: Not A Card\n"


def test_included_combos_carry_spellbooks_two_card_mark_and_flags_and_stay_in_colour(combos, monkeypatch):
    deck("braids", "Braids, Arisen Nightmare", {"Ashnod's Altar": 1, "Gravecrawler": 1, "Phyrexian Altar": 1,
                                                "Pitiless Plunderer": 1, "Reassembling Skeleton": 1},
         adds=["Lieutenant Commander Data", "Warren Soultrader", "Zulaport Cutthroat"])
    bracket = json.loads((SAVED / "braids-estimate-bracket.json").read_text())
    bracket["combos"][0]["arguablyTwoCard"] = bracket["combos"][1]["definitelyTwoCard"] = True
    bracket["cards"][0]["massLandDenial"] = bracket["cards"][0]["extraTurn"] = True
    answering(combos, monkeypatch, BRACKET, json.dumps(bracket).encode())
    assert write(combos, "braids") == """# braids: combos from commanderspellbook.com

## Included
| Cards | Result | Two-card | Bracket tag | Salt |
|---|---|---|---|---|
| Gravecrawler + Phyrexian Altar | Infinite death triggers, Infinite creature ETB, Infinite creature LTB, Infinite creature sacrifice triggers, Infinite storm count | definite | Exhibition | 2.5 |
| Pitiless Plunderer + Ashnod's Altar + Reassembling Skeleton | Infinite colorless mana, Infinite death triggers, Infinite creature ETB, Infinite creature LTB, Infinite creature sacrifice triggers | arguable | Exhibition | 1.4 |

## Almost included
| Missing | Present | Result | Bracket tag | Salt |
|---|---|---|---|---|

## Flagged cards
| Card | Flag |
|---|---|
| Ashnod's Altar | mass land denial |
| Ashnod's Altar | extra turns |
"""


def test_a_cached_variants_file_is_read_until_it_is_a_day_old(combos):
    deck("braids", "Braids, Arisen Nightmare", {"Gravecrawler": 1, "Phyrexian Altar": 1})
    CACHED.write_bytes(gzip.compress(b'{"variants": []}'))
    assert "| Gravecrawler + Phyrexian Altar |" not in write(combos, "braids")
    assert [u for u, _ in combos.asked] == [BRACKET]
    combos.variants.cache_clear()
    os.utime(CACHED, (time.time() - 24 * 60 * 60 - 60,) * 2)
    assert "| Gravecrawler + Phyrexian Altar |" in write(combos, "braids")
    assert gzip.decompress(CACHED.read_bytes()) == (SAVED / "variants.json").read_bytes()


@pytest.mark.parametrize("answer", [URLError("down"), Failed(f"{BULK}: HTTP 503"), b"<title>Just a moment...</title>"])
def test_a_stale_cached_variants_file_is_used_when_spellbook_sends_none(combos, monkeypatch, capsys, answer):
    deck("braids", "Braids, Arisen Nightmare", {"Gravecrawler": 1, "Phyrexian Altar": 1})
    CACHED.write_bytes(gzip.compress((SAVED / "variants.json").read_bytes()))
    old = time.mktime((2026, 11, 2, 12, 0, 0, 0, 0, -1))
    os.utime(CACHED, (old, old))
    answering(combos, monkeypatch, BULK, answer)
    text = write(combos, "braids")
    assert text.startswith("# braids: combos from commanderspellbook.com, from a stale copy of 2026-11-02\n")
    assert "| Gravecrawler + Phyrexian Altar |" in text
    assert CACHED.stat().st_mtime == old and capsys.readouterr().out == ""


@pytest.mark.parametrize("answer, url", [
    (URLError("down"), BULK),
    (Failed(f"{BULK}: HTTP 503"), BULK),
    (b"<title>Just a moment...</title>", BULK),
    (URLError("down"), BRACKET),
    (b"<title>Just a moment...</title>", BRACKET),
])
def test_no_answer_from_spellbook_names_the_url_and_writes_nothing(combos, monkeypatch, capsys, answer, url):
    deck("beamtown", "The Beamtown Bullies", {"Seeker of Skybreak": 1})
    answering(combos, monkeypatch, url, answer)
    combos.write("run", "beamtown")
    assert capsys.readouterr().out == f"Commander Spellbook unreachable: {url}\n"
    assert not Path("run/beamtown-combos.md").exists()
    assert CACHED.exists() == (url == BRACKET)


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
    # cheap: Mox, Sol Ring, Ritual, Signet add mana; Arena draws but costs three. 31.42 + 3.13 * 26/9 - 0.28 * 4
    # U needs: Lazav 4UU 26, Counterspell UU 30, Sphinx 5UU 20. B: Ritual B 19, Lazav 26, Arena 1BB 28, Wurm 3BBB 28
    assert read("run/lazav-mana.md") == """# lazav: mana

## Curve
| Lands | Karsten lands | Nonlands | Mean mana value | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7+ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 13 | 39.3 | 9 | 2.9 | 1 | 2 | 2 | 1 | 1 | 0 | 1 | 1 |

## Opening seven
| 2 lands | 3 lands | 4 lands |
|---|---|---|
| 4% | 17% | 34% |

## Colours
| Colour | Land sources | Karsten sources | For | Nonland sources | Pips | Cards with 2+ pips | Lowest mana value of those |
|---|---|---|---|---|---|---|---|
| U | 10 | 30 | Counterspell | 2 | 6 | 3 | 2 |
| B | 7 | 28 | Phyrexian Arena | 3 | 8 | 3 | 3 |
"""


def test_mana_reads_a_cost_off_karstens_table_as_the_listed_one_below_it():
    oracle = {"Kraken": {"name": "Kraken", "type_line": "Legendary Creature", "cmc": 8, "mana_cost": "{6}{U}{U}",
                         "color_identity": ["B", "U"]},
              "Bog Thing": {"name": "Bog Thing", "type_line": "Creature", "cmc": 9, "mana_cost": "{8}{B}"},
              "Swamp Spirit": {"name": "Swamp Spirit", "type_line": "Creature", "cmc": 2, "mana_cost": "{1}{B}",
                               "oracle_text": "When this creature enters, draw a card."},
              "Swamp": {"name": "Swamp", "type_line": "Basic Land — Swamp", "cmc": 0, "produced_mana": ["B"]}}
    Path("output/data/oracle.json").write_text(json.dumps({"cards": oracle}))
    deck("kraken", "Kraken", {"Bog Thing": 1, "Swamp Spirit": 1, "Swamp": 6})
    Path("run").mkdir()
    mana.write("run", "kraken")
    # 6UU reads as 5UU, 20; 8B as 5B, 14, below Swamp Spirit's 1B, 19. 31.42 + 3.13 * 19/3 - 0.28 * 1
    assert "| 6 | 51.0 | 3 | 6.3 |" in read("run/kraken-mana.md")
    assert "| B | 6 | 19 | Swamp Spirit |" in read("run/kraken-mana.md")
    assert "| U | 0 | 20 | Kraken |" in read("run/kraken-mana.md")
    assert (karsten.sources(9, 1), karsten.sources(5, 5), karsten.sources(9, 3)) == (14, 36, 26)


@pytest.mark.parametrize("value, text, creature, cheap", [
    (1, "Look at the top three cards of your library, then put one into your hand.", False, True),
    (1, "Look at the top three cards of your library, then put one into your hand. You may pay 2 life.", False, False),
    (2, "When this creature enters, draw a card.", True, True),
    (2, "Whenever this creature attacks, draw a card.", True, False),
    (2, "Draw a card. Create a Blood token.", False, False),
    (3, "Draw two cards.", False, False),
    (2, "Flying\nCycling {U} ({U}, Discard this card: Draw a card.)", True, True),
    (2, "Flying\nCycling {2} ({2}, Discard this card: Draw a card.)", True, False),
    (2, "When this creature dies, add {B}{B}.", True, False),
    (2, "Search your library for a basic land card, put it onto the battlefield tapped, then shuffle.", False, True),
    (2, "Sacrifice this: Search your library for a basic land card, put it onto the battlefield.", False, False),
    (2, "Whenever enchanted land is tapped for mana, its controller adds an additional {G}.", False, True),
    (2, "{T}: You may put a creature card with mana value 3 or less from your hand onto the battlefield.", True, True),
])
def test_karsten_counts_cheap_draw_and_ramp_by_his_oracle_text_rules(value, text, creature, cheap):
    assert karsten.cheap(value, text, creature) == cheap


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
| Lands | Karsten lands | Nonlands | Mean mana value | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7+ |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 | 36.1 | 2 | 1.5 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |

## Opening seven
| 2 lands | 3 lands | 4 lands |
|---|---|---|
| unknown | unknown | unknown |

## Colours
| Colour | Land sources | Karsten sources | For | Nonland sources | Pips | Cards with 2+ pips | Lowest mana value of those |
|---|---|---|---|---|---|---|---|
| U | 5 | 19 | Zara, Tide Caller | 0 | 1 | 0 | - |
"""


def test_facts_writes_both_files_per_deck(combos, monkeypatch):
    deck("beamtown", "The Beamtown Bullies", {"Sol Ring": 1, "Island": 7})
    deck("braids", "Braids, Arisen Nightmare", {"Sol Ring": 1, "Island": 7})
    monkeypatch.setattr(sys, "argv", ["facts.py", "run", "beamtown", "braids"])
    facts.main()
    assert sorted(p.name for p in Path("run").iterdir()) == ["beamtown-combos.md", "beamtown-mana.md",
                                                             "braids-combos.md", "braids-mana.md"]
