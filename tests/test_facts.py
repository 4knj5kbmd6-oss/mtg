import gzip, json, os, sys, time
from math import comb
from pathlib import Path
from urllib.error import URLError
import pytest
from conftest import ROOT, run, read
import combos as script, facts, mana, odds
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
    # U needs: Lazav UU by turn 4 6, Counterspell UU by turn 2 7, Sphinx UU by turn 7 4
    # B needs: Ritual B by turn 1 5, Lazav BB by turn 4 6, Arena BB by turn 3 6, Wurm BBB by turn 6 7
    assert read("run/lazav-mana.md") == """# lazav: mana

## Curve
| Lands | Nonlands | Mean mana value | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7+ |
|---|---|---|---|---|---|---|---|---|---|---|
| 13 | 9 | 2.9 | 1 | 2 | 2 | 1 | 1 | 0 | 1 | 1 |

## Lands
| 2 by turn 2 | 3 by turn 3 | 4 by turn 4 |
|---|---|---|
| 100% | 100% | 100% |

## Colours
| Colour | Land sources | Sources needed | For | Nonland sources | Pips | Cards with 2+ pips | Lowest mana value of those |
|---|---|---|---|---|---|---|---|
| U | 10 | 7 | Counterspell | 2 | 6 | 3 | 2 |
| B | 7 | 7 | Massacre Wurm | 3 | 8 | 3 | 3 |
"""


def test_mana_needs_the_sources_that_cast_a_card_on_curve_nine_times_in_ten():
    cost = lambda name, value, cost: {"name": name, "type_line": "Artifact", "cmc": value, "mana_cost": cost}
    oracle = {"Zara, Tide Caller": {**cost("Zara, Tide Caller", 2, "{2}"), "color_identity": ["U"]},
              "Counterspell": cost("Counterspell", 2, "{U}{U}"), "Kraken": cost("Kraken", 9, "{7}{U}{U}"),
              "Filler": cost("Filler", 2, "{2}"),
              "Island": {"name": "Island", "type_line": "Basic Land — Island", "cmc": 0, "produced_mana": ["U"]}}
    Path("output/data/oracle.json").write_text(json.dumps({"cards": oracle}))
    deck("counter", "Zara, Tide Caller", {"Island": 37, "Filler": 61, "Counterspell": 1})
    deck("kraken", "Zara, Tide Caller", {"Island": 37, "Filler": 61, "Kraken": 1})
    Path("run").mkdir()
    mana.write("run", "counter")
    mana.write("run", "kraken")
    # Counterspell sees 9 of the 99 by turn 2, given 2 or more of the 37 lands among them: k lands come
    # C(37, k) C(62, 9-k) ways, and 2 or more of S sources among k lands is 1 - (C(37-S, k) + S C(37-S, k-1)) / C(37, k);
    # summed over k from 2 to 9 and divided by the ways of 2 or more lands: 0.9161 at 31, 0.8978 at 30
    lands = lambda k, seen: comb(37, k) * comb(62, seen - k)
    two = lambda s, k: 1 - (comb(37 - s, k) + s * comb(37 - s, k - 1)) / comb(37, k)
    hit = lambda s, seen, least: (sum(lands(k, seen) * two(s, k) for k in range(least, seen + 1))
                                  / sum(lands(k, seen) for k in range(least, seen + 1)))
    assert hit(31, 9, 2) >= 0.9 > hit(30, 9, 2)
    assert "| U | 37 | 31 | Counterspell |" in read("run/counter-mana.md")
    # 37 lands of 99: 2 or more of 9 cards 0.9160, 3 or more of 10 0.8004, 4 or more of 11 0.6488
    assert "|---|---|---|\n| 92% | 80% | 65% |\n" in read("run/counter-mana.md")
    # Kraken's mana value 9 reads as turn 7: 14 cards seen, given 9 or more lands; 0.9208 at 13 sources, 0.8894 at 12
    assert hit(13, 14, 9) >= 0.9 > hit(12, 14, 9)
    assert "| U | 37 | 13 | Kraken |" in read("run/kraken-mana.md")


def test_mana_never_needs_more_sources_than_lands():
    cost = lambda name, value, cost: {"name": name, "type_line": "Artifact", "cmc": value, "mana_cost": cost}
    oracle = {"Zara, Tide Caller": {**cost("Zara, Tide Caller", 2, "{2}"), "color_identity": ["U"]},
              "Cryptic": cost("Cryptic", 3, "{U}{U}{U}"), "Filler": cost("Filler", 2, "{2}"),
              "Island": {"name": "Island", "type_line": "Basic Land — Island", "cmc": 0, "produced_mana": ["U"]}}
    Path("output/data/oracle.json").write_text(json.dumps({"cards": oracle}))
    deck("mono", "Zara, Tide Caller", {"Island": 10, "Filler": 88, "Cryptic": 1})
    Path("run").mkdir()
    mana.write("run", "mono")
    # every land an Island: given 3 or more lands among 10 cards, all 10 always cast Cryptic; 9 do 0.7416 of the time
    assert "| U | 10 | 10 | Cryptic |" in read("run/mono-mana.md")


def test_odds_count_the_hits_among_the_cards_seen():
    # 2 hits in a deck of 4, 2 drawn: both 1 in C(4, 2) = 6, at least one 5 in 6; turn one already sees a draw
    assert (odds.at_least(1, 2, 4, 2), odds.at_least(2, 2, 4, 2), odds.seen(1)) == (5 / 6, 1 / 6, 8)


def test_odds_given_lands_count_only_the_draws_that_hit_them():
    # 2 lands in a deck of 4, 1 a source, 2 drawn: one land 4 ways, a source half of them; both lands 1 way, a source
    # always; at least one land 5 ways, so (4 x 1/2 + 1) / 5
    assert odds.given_lands(1, 1, 2, 4, 2, 1) == 3 / 5


def test_mana_odds_are_unknown_with_fewer_known_cards_than_are_seen(capsys):
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

## Lands
| 2 by turn 2 | 3 by turn 3 | 4 by turn 4 |
|---|---|---|
| unknown | unknown | unknown |

## Colours
| Colour | Land sources | Sources needed | For | Nonland sources | Pips | Cards with 2+ pips | Lowest mana value of those |
|---|---|---|---|---|---|---|---|
| U | 5 | unknown | - | 0 | 1 | 0 | - |
"""


def test_facts_writes_both_files_per_deck(combos, monkeypatch):
    deck("beamtown", "The Beamtown Bullies", {"Sol Ring": 1, "Island": 7})
    deck("braids", "Braids, Arisen Nightmare", {"Sol Ring": 1, "Island": 7})
    monkeypatch.setattr(sys, "argv", ["facts.py", "run", "beamtown", "braids"])
    facts.main()
    assert sorted(p.name for p in Path("run").iterdir()) == ["beamtown-combos.md", "beamtown-mana.md",
                                                             "braids-combos.md", "braids-mana.md"]
