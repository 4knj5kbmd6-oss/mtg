import gzip, json, os, random, sys, time
from itertools import product
from math import comb
from pathlib import Path
from urllib.error import URLError
import pytest
from conftest import ROOT, run, read
import combos as script, facts, mana, odds, recommend
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


def recommendation(text):
    """the Recommendation row's Lands and each colour's sources"""
    row = [c.strip() for c in text.split("## Recommendation\n")[1].splitlines()[2].strip("|").split("|")]
    return int(row[0]), [int(c.split("(")[1].rstrip(")")) for c in row[2:]]


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

## Recommendation
| Lands | Lands now | U | B |
|---|---|---|---|
| 8 | 13 | 40% (3) | 60% (5) |
"""
    # ramp: Mox Opal, Sol Ring, Arcane Signet (Dark Ritual is an instant); 3/8 and 5/8 tie on remainder, U first
    lands, sources = recommendation(read("run/lazav-mana.md"))
    assert 0 <= lands <= 21 - 3 and sum(sources) == lands


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

## Recommendation
| Lands | Lands now | U |
|---|---|---|
| unknown | 5 | unknown |
"""


def test_mana_recommends_the_lands_and_split_that_cast_the_most_spells_on_time():
    card = lambda name, cost: {"name": name, "type_line": "Artifact", "cmc": 1, "mana_cost": cost, "oracle_text": ""}
    land = lambda name, colour: {"name": name, "type_line": f"Basic Land — {name}", "cmc": 0, "produced_mana": [colour]}
    oracle = {"Ixi, Tide Caller": {**card("Ixi, Tide Caller", "{U}"), "type_line": "Legendary Creature",
                                   "color_identity": ["B", "U"]},
              "Island": land("Island", "U"), "Swamp": land("Swamp", "B"), "Sprite": card("Sprite", "{U}"),
              "Imp": card("Imp", "{B}")}
    Path("output/data/oracle.json").write_text(json.dumps({"cards": oracle}))
    deck("ixi", "Ixi, Tide Caller", {"Island": 4, "Swamp": 3, "Sprite": 9, "Imp": 4})
    Path("run").mkdir()
    mana.write("run", "ixi")
    C = lambda n, k: comb(n, k) if 0 <= k <= n else 0
    H = recommend.HORIZON
    # 20 cards, no ramp, every card due on turn 1, so on time is a land among the other cards seen by the turn it is
    # cast: turn 1 from the opening 7 or the first draw (8 places of 20, 7 others seen), else the turn d it is drawn
    # (6 + d others seen); q(L, n) is a land among n of the 19 others. The commander needs a land among 8 of the 20,
    # and the 13 spells fill 20 - L places
    q = lambda L, n: 1 - C(19 - L, n) / C(19, n)
    V = lambda L: 1 - C(20 - L, 8) / C(20, 8) + (20 - L) * (8 * q(L, 7) + sum(q(L, 6 + d) for d in range(2, H + 1))) / 20
    assert [round(V(L), 3) for L in (3, 4, 5)] == [13.279, 13.517, 13.231] and max(range(21), key=V) == 4
    # at 4 lands, k of them among the 7 others a spell sees by turn 1 (the commander: 8 of 20), given 1 or more: a {U}
    # card is met unless the k all miss the u Islands; the 13 spells count 16/13 each
    def met(u, pool, seen):
        ways = {k: C(4, k) * C(pool - 4, seen - k) for k in range(1, 5)}
        return sum(w * (1 - C(4 - u, k) / C(4, k)) for k, w in ways.items()) / sum(ways.values())
    G = lambda u: met(u, 20, 8) + 16 / 13 * (9 * met(u, 19, 7) + 4 * met(4 - u, 19, 7))
    assert [round(G(u), 3) for u in (2, 3, 4)] == [11.99, 12.794, 12.077] and max(range(5), key=G) == 3
    text = read("run/ixi-mana.md")
    assert "## Recommendation\n| Lands | Lands now | U | B |\n|---|---|---|---|\n| 4 | 7 | 75% (3) | 25% (1) |\n" in text
    lands, sources = recommendation(text)
    assert 0 <= lands <= 20 and sum(sources) == lands


def test_odds_mana_counts_ramp_from_the_turn_after_it_is_drawn():
    # 1 land drop, 1 ramp and 2 others, 2 drawn on turn 1: only {land, ramp} of the 6 pairs makes 2 mana, and when one
    # of the drawn is the turn's draw it is the ramp half the time
    assert odds.mana(2, 1, 4, 2, 1, 1, False) == 1 / 6
    assert odds.mana(2, 1, 4, 2, 1, 1, True) == pytest.approx(1 / 12)


def test_odds_met_needs_every_colours_pips():
    # 2 U and 2 B lands, both of 2 drawn lands: one of each in 4 of the 6 pairs
    table = odds.lands_seen(4, 4, 2, 2, 1)
    assert odds.met([2, 2], [1, 1], table) == pytest.approx(2 / 3)


def test_split_matches_the_exhaustive_optimum():
    rng = random.Random(3)
    for identity, lands in ((["W", "U", "B"], 20), (["W", "U", "B", "G"], 12)):
        spells = []
        for _ in range(30):
            colours = rng.sample(identity, rng.choice([1, 1, 1, 2, 3]))
            need = {c: rng.choice([1, 1, 2]) if len(colours) == 1 else 1 for c in identity if c in colours}
            spells.append((rng.randint(1, 10), rng.random() < 0.2, max(sum(need.values()), rng.randint(1, 5)), need))
        commanders = [(8, 3, {identity[0]: 1, identity[-1]: 1})]
        every = [s for s in product(range(lands + 1), repeat=len(identity)) if sum(s) == lands]
        value = {s: recommend.worth(dict(zip(identity, s)), lands, 60, identity, spells, commanders) for s in every}
        best = max(s for s in every if value[s] >= max(value.values()) - 1e-9)
        assert recommend.split(lands, 60, identity, spells, commanders) == dict(zip(identity, best))


def test_shares_are_fives_summing_to_100():
    # 3/8 and 5/8 of 20 are 7.5 and 12.5: the remainders tie, so the first colour takes the twentieth left over
    assert recommend.shares({"U": 3, "B": 5}) == {"U": 40, "B": 60}
    assert recommend.shares({"W": 1, "U": 1, "B": 1}) == {"W": 35, "U": 35, "B": 30}
    for lands in range(1, 46):
        two = [(a, lands - a) for a in range(lands + 1)]
        for s in two + [(a, b, rest - b) for a, rest in two for b in range(rest + 1)]:
            got = list(recommend.shares(dict(zip("WUB", s))).values())
            assert sum(got) == 100 and all(p % 5 == 0 and abs(p - 100 * c / lands) <= 5 for p, c in zip(got, s))


RAMP = {  # name: (type, cost, mana value, oracle text)
    "Llanowar Elves": ("Creature — Elf Druid", "{G}", 1, "{T}: Add {G}."),
    "Sol Ring": ("Artifact", "{1}", 1, "{T}: Add {C}{C}."),
    "Arcane Signet": ("Artifact", "{2}", 2, "{T}: Add one mana of any color in your commander's color identity."),
    "Rakdos Signet": ("Artifact", "{2}", 2, "{1}, {T}: Add {B}{R}."),
    "Wild Growth": ("Enchantment — Aura", "{G}", 1, "Enchant land\nWhenever enchanted land is tapped for mana, its controller adds an additional {G}."),
    "Rampant Growth": ("Sorcery", "{1}{G}", 2, "Search your library for a basic land card, put that card onto the battlefield tapped, then shuffle."),
    "Sakura-Tribe Elder": ("Creature — Snake Shaman", "{1}{G}", 2, "Sacrifice this creature: Search your library for a basic land card, put that card onto the battlefield tapped, then shuffle."),
}
NOT_RAMP = {
    "Lotus Petal": ("Artifact", "{0}", 0, "{T}, Sacrifice this artifact: Add one mana of any color."),
    "Dark Ritual": ("Instant", "{B}", 1, "Add {B}{B}{B}."),
    "Path to Exile": ("Instant", "{W}", 1, "Exile target creature. Its controller may search their library for a basic land card, put that card onto the battlefield tapped, then shuffle."),
    "Harrow": ("Instant", "{2}{G}", 3, "As an additional cost to cast this spell, sacrifice a land.\nSearch your library for up to two basic land cards, put them onto the battlefield, then shuffle."),
    "Bubbling Muck": ("Sorcery", "{B}", 1, "Until end of turn, whenever a player taps a Swamp for mana, that player adds an additional {B}."),
    "Greedy Freebooter": ("Creature — Human Pirate", "{B}", 1, 'When this creature dies, scry 1 and create a Treasure token. (To scry 1, look at the top card of your library. You may put that card on the bottom. A Treasure token is an artifact with "{T}, Sacrifice this token: Add one mana of any color.")'),
    "Ashnod's Altar": ("Artifact", "{3}", 3, "Sacrifice a creature: Add {C}{C}."),
}
FACES = {  # name: (front, back), each (type, cost, mana value, oracle text)
    "Malakir Rebirth // Malakir Mire": (
        ("Instant", "{B}", 1, 'Choose target creature. You lose 2 life. Until end of turn, that creature gains "When this creature dies, return it to the battlefield tapped under its owner\'s control."'),
        ("Land", "", 0, "This land enters tapped.\n{T}: Add {B}.")),
    "Search for Azcanta // Azcanta, the Sunken Ruin": (
        ("Legendary Enchantment", "{1}{U}", 2, "At the beginning of your upkeep, look at the top card of your library. You may put it into your graveyard. Then if you have seven or more cards in your graveyard, you may transform Search for Azcanta."),
        ("Legendary Land", "", 0, "(Transforms from Search for Azcanta.)\n{T}: Add {U}.\n{2}{U}, {T}: Look at the top four cards of your library. You may reveal a noncreature, nonland card from among them and put it into your hand. Put the rest on the bottom of your library in any order.")),
}


def test_ramp_and_land_drops_read_from_oracle_text():
    entry = lambda name, kind, cost, value, text: {"name": name, "type_line": kind, "mana_cost": cost, "cmc": value,
                                                   "oracle_text": text}
    assert [n for n, card in RAMP.items() if mana.ramp(entry(n, *card))] == list(RAMP)
    assert [n for n, card in NOT_RAMP.items() if mana.ramp(entry(n, *card))] == []
    # a modal land is a land drop and not ramp; a card that transforms into a land is neither
    faced = {n: {"name": n, "cmc": front[2], "card_faces": [entry(n, *front), entry(n, *back)]}
             for n, (front, back) in FACES.items()}
    assert [(mana.land_drop(e), mana.ramp(e)) for e in faced.values()] == [(True, False), (False, False)]


def test_facts_writes_both_files_per_deck(combos, monkeypatch):
    deck("beamtown", "The Beamtown Bullies", {"Sol Ring": 1, "Island": 7})
    deck("braids", "Braids, Arisen Nightmare", {"Sol Ring": 1, "Island": 7})
    monkeypatch.setattr(sys, "argv", ["facts.py", "run", "beamtown", "braids"])
    facts.main()
    assert sorted(p.name for p in Path("run").iterdir()) == ["beamtown-combos.md", "beamtown-mana.md",
                                                             "braids-combos.md", "braids-mana.md"]
