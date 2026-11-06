import gzip, json, os, sys, time
from pathlib import Path
from urllib.error import URLError
import pytest
from conftest import ROOT, read
import combos as script, facts
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


def cached():
    return json.loads(gzip.decompress(CACHED.read_bytes()))


def slimmed():
    """the saved variants file as the cache keeps it: no timestamp or version"""
    return {"variants": json.loads((SAVED / "variants.json").read_text())["variants"]}


def test_the_cache_keeps_only_the_fields_read_and_rereads_to_the_same_combos():
    full = json.loads((SAVED / "variants.json").read_text())
    for v in full["variants"]:
        v.update(description="Tap and sacrifice.", legalities={"commander": True}, prices={"tcgplayer": "1.00"})
        for u in v["uses"]: u.update(zoneLocations=["B"], card={**u["card"], "id": 1, "oracleId": "x"})
        for p in v["produces"]: p["feature"]["id"] = 2
    bulk = gzip.compress(json.dumps(full).encode())
    slim = script.slim(bulk)
    kept = json.loads(gzip.decompress(slim))
    assert kept == slimmed()
    assert {*kept["variants"][0]} == {"id", "uses", "produces", "identity", "bracketTag", "salt", "popularity"}
    assert script.parse(slim) == script.parse(bulk) != []


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
    assert cached() == slimmed()
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
    assert cached() == slimmed()


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


def test_facts_writes_two_files_per_deck(combos, monkeypatch):
    deck("beamtown", "The Beamtown Bullies", {"Sol Ring": 1, "Island": 7})
    deck("braids", "Braids, Arisen Nightmare", {"Sol Ring": 1, "Island": 7})
    monkeypatch.setattr(sys, "argv", ["facts.py", "run", "beamtown", "braids"])
    facts.main()
    assert sorted(p.name for p in Path("run").iterdir()) == [f"{d}-{f}.md" for d in ("beamtown", "braids")
                                                             for f in ("combos", "counts")]


def test_counts_put_the_fixture_decks_cards_in_categories_by_their_tags():
    oracle = json.loads(read("output/data/oracle.json"))
    tags = {"Coral Signet": ["protection", "recursion"],
            "Tidal Insight": ["counterspell", "draw"],  # an instant
            "Wave Breaker": ["removal", "spot removal"],  # with flash, below
            "Brine Elemental": ["removal", "removal-creature", "sweeper"],  # a sweeper is a wipe, not removal
            "Sunken Grotto": ["hate", "hate-graveyard"]}
    for name, t in tags.items(): oracle["cards"][name]["tags"] = t
    oracle["cards"]["Wave Breaker"]["oracle_text"] = "Flash, haste"
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    Path("run").mkdir()
    facts.counts("run", "zara")
    assert read("run/zara-counts.md") == """# zara: counts

| Category | Count | Cards |
|---|---|---|
| Recursion | 1 | Coral Signet |
| Protection | 1 | Coral Signet |
| Answers | 4 | Brine Elemental; Sunken Grotto; Tidal Insight; Wave Breaker |
| Instant-speed answers | 2 | Tidal Insight; Wave Breaker |
| Counters | 1 | Tidal Insight |
| Removal | 1 | Wave Breaker |
| Wipes | 1 | Brine Elemental |
| Salt | 1 | mean 0.00 over 0 cards; - |
"""


def salted(values):
    """oracle.json with these salt values"""
    oracle = json.loads(read("output/data/oracle.json"))
    for name, value in values.items(): oracle["cards"][name]["salt"] = value
    Path("output/data/oracle.json").write_text(json.dumps(oracle))


def test_salt_is_the_mean_over_every_copy_without_plain_lands_or_unknown_salt():
    salted({"Zara, Tide Caller": 0.3, "Brine Elemental": 0.1, "Coral Signet": 0.1, "Sol Ring": 2.1, "Tidal Insight": 0.2,
            "Wave Breaker": 0.1, "Sunken Grotto": 0.5,  # a land at 0.5 counts
            "Island": 0.05, "Misty Cove": 0.49})  # a basic and a land under 0.5 do not; Kelp Weaver has no value
    list_ = Path("output/decks/zara/list.txt")
    list_.write_text(list_.read_text().replace("1 Sol Ring", "2 Sol Ring") + "\nSIDEBOARD:\n1 Pearl Diver\n")
    salted({"Pearl Diver": 3.0})  # the SIDEBOARD block is not the deck
    mean, n, level, salty = facts.salt("zara")
    # (0.3 + 0.1 + 0.1 + 2 * 2.1 + 0.2 + 0.1 + 0.5) / 8 = 0.6875, level 1 + 8 * 0.3875 / 0.6 = 6.2
    assert (round(mean, 4), n, level, salty) == (0.6875, 8, 6, [("Sol Ring", 2.1)])
    Path("run").mkdir()
    facts.counts("run", "zara")
    assert read("run/zara-counts.md").endswith("| Salt | 6 | mean 0.69 over 8 cards; Sol Ring 2.1 |\n")


@pytest.mark.parametrize("value, level", [(0.3, 1), (0.6, 5), (0.9, 9), (0.1, 1), (1.4, 9), (0.65, 6)])
def test_salt_level_runs_from_1_at_a_mean_of_030_to_9_at_090(value, level):
    salted({"Zara, Tide Caller": value})
    Path("output/decks/zara/list.txt").write_text("1 Zara, Tide Caller\n")
    assert facts.salt("zara")[2] == level
