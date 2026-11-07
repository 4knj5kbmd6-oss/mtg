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


@pytest.mark.parametrize("answer", [URLError("down"), Failed(f"{BULK}: HTTP 503"), b"<title>Just a moment...</title>",
                                    gzip.compress(b'{"detail": "x"}'), gzip.compress(b"[]")])
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
    (gzip.compress(b'{"detail": "x"}'), BULK),
    (URLError("down"), BRACKET),
    (b"<title>Just a moment...</title>", BRACKET),
    (b'{"detail": "x"}', BRACKET),
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


def test_facts_writes_the_counts_when_spellbook_answers_without_cards_or_combos(combos, monkeypatch, capsys):
    deck("beamtown", "The Beamtown Bullies", {"Sol Ring": 1})
    answering(combos, monkeypatch, BRACKET, b'{"detail": "x"}')
    monkeypatch.setattr(sys, "argv", ["facts.py", "run", "beamtown"])
    facts.main()
    assert capsys.readouterr().out == f"Commander Spellbook unreachable: {BRACKET}\n"
    assert sorted(p.name for p in Path("run").iterdir()) == ["beamtown-counts.md"]


def test_facts_names_the_list_cards_oracle_json_lacks_commanders_in(combos, monkeypatch, capsys):
    deck("braids", "Braids, Arisen Nightmare", {"Sol Ring": 1, "Not A Card": 1})
    oracle = json.loads(read("output/data/oracle.json"))
    oracle["cards"].pop("Braids, Arisen Nightmare")
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    monkeypatch.setattr(sys, "argv", ["facts.py", "run", "braids"])
    facts.main()
    assert "braids: not in oracle.json: Braids, Arisen Nightmare, Not A Card" in capsys.readouterr().out.splitlines()


def test_a_deck_after_one_spellbook_fails_still_gets_its_files(combos, monkeypatch, capsys):
    deck("beamtown", "The Beamtown Bullies", {"Sol Ring": 1})
    deck("braids", "Braids, Arisen Nightmare", {"Sol Ring": 1})
    saved = combos.get
    beamtown = lambda body: body and body["commanders"][0]["card"] == "The Beamtown Bullies"
    monkeypatch.setattr(combos, "get", lambda url, body=None: b'{"detail": "x"}' if beamtown(body) else saved(url, body))
    monkeypatch.setattr(sys, "argv", ["facts.py", "run", "beamtown", "braids"])
    facts.main()
    assert f"Commander Spellbook unreachable: {BRACKET}" in capsys.readouterr().out.splitlines()
    assert sorted(p.name for p in Path("run").iterdir()) == ["beamtown-counts.md", "braids-combos.md", "braids-counts.md"]


def test_counts_put_the_fixture_decks_cards_in_categories_by_their_tags():
    oracle = json.loads(read("output/data/oracle.json"))
    tags = {"Coral Signet": ["protection", "recursion"],
            "Tidal Insight": ["counterspell", "draw"],  # an instant
            "Wave Breaker": ["removal", "removal-creature", "spot removal"],  # with flash, below
            "Brine Elemental": ["removal", "removal-creature", "sweeper"],  # a wipe, not removal, but creature removal
            "Sunken Grotto": ["hate", "hate-graveyard"]}
    for name, t in tags.items(): oracle["cards"][name]["tags"] = t
    oracle["cards"]["Wave Breaker"]["oracle_text"] = "Flash, haste"
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    Path("run").mkdir()
    facts.counts("run", "zara", 3)
    assert read("run/zara-counts.md") == """# zara: counts

| Category | Count | Cards |
|---|---|---|
| Recursion | 1 | Coral Signet |
| Protection | 1 | Coral Signet |
| Answers | 4 | Brine Elemental; Sunken Grotto; Tidal Insight; Wave Breaker |
| Instant-speed answers | 2 | Tidal Insight; Wave Breaker |
| Counters | 1 | Tidal Insight |
| Removal | 1 | Wave Breaker |
| Creature removal | 2 | Brine Elemental; Wave Breaker |
| Noncreature removal | 0 | - |
| Wipes | 1 | Brine Elemental |
| Game Changers | 0 | - |
| Commander salt | 1 | sum 0.00; - |
| Commander price | 1 | sum $0.00; - |
| 99 salt | 1 | mean 0.00 over 0 cards; - |
| 99 price | 1 | sum $0.00 over 0 cards, 0 priciest out: - |
"""


def test_creature_and_noncreature_removal_count_removal_and_wipes_by_target_tags_or_else_by_text():
    oracle = json.loads(read("output/data/oracle.json"))
    tags = {"Wave Breaker": ["removal", "removal-burn", "removal-creature"],
            "Kelp Weaver": ["removal", "removal-aura", "removal-enchantment"],  # an aura's parent tag is enchantment
            "Sol Ring": ["removal", "removal-sacrifice"],  # no target tag: its text names a permanent, both
            "Coral Signet": ["removal"],  # no target tag: its text names an artifact
            "Brine Elemental": ["removal"],  # no target tag and its text names no target
            "Tidal Insight": ["removal", "removal-creature", "sweeper"]}  # a wipe, not removal, counts for the kind it hits
    for name, t in tags.items(): oracle["cards"][name]["tags"] = t
    oracle["cards"]["Sol Ring"]["oracle_text"] = "Each opponent sacrifices a nonland permanent."
    oracle["cards"]["Coral Signet"]["oracle_text"] = "Exile target artifact."
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    Path("run").mkdir()
    facts.counts("run", "zara", 3)
    got = read("run/zara-counts.md")
    assert "\n| Removal | 5 | Brine Elemental; Coral Signet; Kelp Weaver; Sol Ring; Wave Breaker |\n" \
           "| Creature removal | 3 | Sol Ring; Tidal Insight; Wave Breaker |\n" \
           "| Noncreature removal | 3 | Coral Signet; Kelp Weaver; Sol Ring |\n| Wipes | 1 | Tidal Insight |\n" in got


def test_counts_name_the_game_changers_of_the_list_without_its_sideboard():
    oracle = json.loads(read("output/data/oracle.json"))
    for name in ("Sol Ring", "Drowned Scholar // Tidal Insight", "Zara, Tide Caller", "Pearl Diver"):
        oracle["cards"][name]["game_changer"] = True
    Path("output/data/oracle.json").write_text(json.dumps(oracle))
    list_ = Path("output/decks/zara/list.txt")
    list_.write_text(list_.read_text().replace("1 Tidal Insight", "1 Drowned Scholar // Tidal Insight")
                     + "\nSIDEBOARD:\n1 Pearl Diver\n")
    assert facts.game_changers("zara") == ["Drowned Scholar", "Sol Ring", "Zara, Tide Caller"]
    Path("run").mkdir()
    facts.counts("run", "zara", 3)
    assert "\n| Game Changers | 3 | Drowned Scholar; Sol Ring; Zara, Tide Caller |\n| Commander salt |" in read("run/zara-counts.md")


def valued(field, values):
    """oracle.json with these values of field, salt or price"""
    oracle = json.loads(read("output/data/oracle.json"))
    for name, value in values.items(): oracle["cards"][name][field] = value
    Path("output/data/oracle.json").write_text(json.dumps(oracle))


def quality(slug="zara", out=0):
    """the deck's Card quality rows, {Category: (level, Cards)}, the out priciest copies of the 99 left out"""
    return {r[0]: (int(r[1]), r[2]) for r in facts.quality(slug, out)}


def test_99_salt_is_the_mean_over_the_99s_copies_without_plain_lands_or_unknown_salt():
    valued("salt", {"Zara, Tide Caller": 0.3, "Brine Elemental": 0.1, "Coral Signet": 0.1, "Sol Ring": 2.1,
                    "Tidal Insight": 0.2, "Wave Breaker": 0.1, "Sunken Grotto": 0.5,  # a land at 0.5 counts
                    "Island": 0.05, "Misty Cove": 0.49,  # a basic and a land under 0.5 do not; Kelp Weaver has no value
                    "Pearl Diver": 3.0})  # the SIDEBOARD block is not the deck
    list_ = Path("output/decks/zara/list.txt")
    list_.write_text(list_.read_text().replace("1 Sol Ring", "2 Sol Ring") + "\nSIDEBOARD:\n1 Pearl Diver\n")
    # (0.1 + 0.1 + 2 * 2.1 + 0.2 + 0.1 + 0.5) / 7 = 0.743, level 1 + 9 * 0.443 / 0.6 = 7.6; the commander's 0.3 apart
    got = quality()
    assert got["99 salt"] == (8, "mean 0.74 over 7 cards; Sol Ring 2.10")
    assert got["Commander salt"] == (1, "sum 0.30; Zara, Tide Caller 0.30")


def test_commander_salt_and_price_add_the_partners():
    Path("output/decks/zara/list.txt").write_text("1 Zara, Tide Caller\n1 Pearl Diver\n\n1 Sol Ring\n")
    valued("salt", {"Zara, Tide Caller": 0.4, "Pearl Diver": 0.35, "Sol Ring": 2.0})
    valued("price", {"Zara, Tide Caller": 6.0, "Pearl Diver": 4.0, "Sol Ring": 1.0})
    got = quality()
    # salt 0.75: 1 + 9 * 0.45 / 0.6 = 7.75; price 10 dollars: 1 + 9 * log10(10) / 2 = 5.5, half up
    assert got["Commander salt"] == (8, "sum 0.75; Zara, Tide Caller 0.40; Pearl Diver 0.35")
    assert got["Commander price"] == (6, "sum $10.00; Zara, Tide Caller $6.00; Pearl Diver $4.00")


def test_99_price_sums_the_99s_copies_and_names_the_cards_at_20_dollars_or_more():
    valued("price", {"Zara, Tide Caller": 4.0, "Sol Ring": 1.5, "Kelp Weaver": 30.0, "Island": 0.25,
                     "Wave Breaker": 20.0, "Pearl Diver": 500.0})  # the rest have no price
    list_ = Path("output/decks/zara/list.txt")
    list_.write_text(list_.read_text().replace("1 Sol Ring", "2 Sol Ring") + "\nSIDEBOARD:\n1 Pearl Diver\n")
    Path("run").mkdir()
    facts.counts("run", "zara", 0)
    # 2 * 1.5 + 30 + 4 * 0.25 + 20 = 54 dollars over 8 copies, under 100 level 1; the commander's 4 dollars
    # 1 + 9 * log10(4) / 2 = 3.7
    assert read("run/zara-counts.md").endswith(
        "| Commander salt | 1 | sum 0.00; - |\n"
        "| Commander price | 4 | sum $4.00; Zara, Tide Caller $4.00 |\n"
        "| 99 salt | 1 | mean 0.00 over 0 cards; - |\n"
        "| 99 price | 1 | sum $54.00 over 8 cards, 0 priciest out: Kelp Weaver $30.00; Wave Breaker $20.00 |\n")


def test_a_99_with_fewer_priced_copies_than_exclude_priciest_leaves_them_all_out():
    valued("price", {"Kelp Weaver": 300.0, "Sol Ring": 1.5})
    assert quality(out=3)["99 price"] == (1, "sum $0.00 over 0 cards, 2 priciest out: Kelp Weaver $300.00; Sol Ring $1.50")


def test_exclude_priciest_leaves_out_copies_highest_first_ties_by_name_so_a_two_copy_card_can_straddle_the_cut():
    valued("price", {"Kelp Weaver": 300.0, "Wave Breaker": 200.0, "Sol Ring": 150.0, "Tidal Insight": 150.0,
                     "Coral Signet": 10.0, "Island": 0.25})
    list_ = Path("output/decks/zara/list.txt")
    list_.write_text(list_.read_text().replace("1 Sol Ring", "2 Sol Ring"))
    # out: Kelp Weaver, Wave Breaker and one Sol Ring, which comes before Tidal Insight by name; kept 150 + 150 + 10
    # + 4 * 0.25 = 311 dollars over 7 copies, 1 + 9 * ln(311 / 100) / ln(20) = 4.4
    assert quality(out=3)["99 price"] == (4, "sum $311.00 over 7 cards, 3 priciest out: Kelp Weaver $300.00; "
                                             "Wave Breaker $200.00; Sol Ring $150.00; Sol Ring $150.00; Tidal Insight $150.00")


@pytest.mark.parametrize("words, row", [
    # settings.json's 1: Kelp Weaver out, 200 dollars kept, 1 + 9 * ln(2) / ln(20) = 3.1
    ([], "| 99 price | 3 | sum $200.00 over 1 cards, 1 priciest out: Kelp Weaver $300.00; Wave Breaker $200.00 |"),
    # the word's 0: 500 dollars kept, 1 + 9 * ln(5) / ln(20) = 5.8
    (["exclude_priciest=0"], "| 99 price | 6 | sum $500.00 over 2 cards, 0 priciest out: Kelp Weaver $300.00; "
                             "Wave Breaker $200.00 |")])
def test_facts_takes_exclude_priciest_from_settings_and_a_key_value_word_overrides_it(monkeypatch, words, row):
    valued("price", {"Kelp Weaver": 300.0, "Wave Breaker": 200.0})
    Path("settings.json").write_text('{"exclude_priciest": 1}')
    monkeypatch.setattr(facts.combos, "write", lambda run, slug: None)
    monkeypatch.setattr(sys, "argv", ["facts.py", "run", "zara", *words])
    Path("run").mkdir()
    facts.main()
    assert f"\n{row}\n" in read("run/zara-counts.md")


# 0.6 is 1 + 9 * 0.3 / 0.6 = 5.5, half up; 0.65 is 6.25
@pytest.mark.parametrize("value, level", [(0.3, 1), (0.6, 6), (0.9, 10), (0.1, 1), (1.4, 10), (0.65, 6)])
def test_salt_levels_run_from_1_at_030_to_10_at_090(value, level):
    Path("output/decks/zara/list.txt").write_text("1 Zara, Tide Caller\n\n1 Sol Ring\n")
    valued("salt", {"Zara, Tide Caller": value, "Sol Ring": value})
    got = quality()
    assert (got["Commander salt"][0], got["99 salt"][0]) == (level, level)


@pytest.mark.parametrize("row, usd, level", [
    ("99 price", 0, 1), ("99 price", 50, 1), ("99 price", 100, 1), ("99 price", 250, 4), ("99 price", 500, 6),
    ("99 price", 1000, 8), ("99 price", 2000, 10), ("99 price", 10000, 10),
    ("Commander price", 0, 1), ("Commander price", 0.5, 1), ("Commander price", 1, 1), ("Commander price", 2, 2),
    ("Commander price", 10, 6), ("Commander price", 50, 9), ("Commander price", 100, 10), ("Commander price", 250, 10)])
def test_price_levels_run_on_a_log_scale_from_100_to_2000_dollars_for_the_99_and_1_to_100_for_the_commanders(
        row, usd, level):
    Path("output/decks/zara/list.txt").write_text("1 Zara, Tide Caller\n\n1 Sol Ring\n")
    valued("price", {"Zara, Tide Caller" if row == "Commander price" else "Sol Ring": usd})
    assert quality()[row][0] == level
