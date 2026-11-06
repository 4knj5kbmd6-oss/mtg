import gzip, importlib, json, sys
from pathlib import Path
import pytest
from conftest import ROOT, run, read, snapshot
import fetch_oracle, net, project, sync

LIST = "output/decks/zara/list.txt"
MOX = ROOT / "tests" / "moxfield" / "mox.json"  # fetch.js's answer: Zara, a new deck, two decks sync skips, a blocked one


def test_changes_in_and_out():
    out = run("skills/sync/apply_changes.py")
    assert out.returncode == 0, out.stderr
    assert out.stdout == "zara: in Deep Current; Pearl Diver | out Wave Breaker | 14 (short 86)\n"
    assert read(LIST).splitlines()[-3:] == ["1 Tidal Insight", "1 Deep Current", "1 Pearl Diver"]
    assert "Wave Breaker" not in read(LIST)
    nonlands = read("output/decks/zara/nonlands.md")
    assert "| Deep Current | 7 | engine | A card on every spell, stacks with Zara |\n| Kelp Weaver |" in nonlands
    assert "Deep Current | 7 | engine | A card on every spell, stacks with Zara | Yes" not in nonlands   # left the Adds table
    assert "Wave Breaker" not in nonlands
    assert nonlands.endswith("10: 1 / 8-9: 1 / 5-7: 4 / 4 or below: 1, mean 6.7 (by card copy), 3 scorers.\n\n"
                             "## Roles\ndraw 2 · ramp 2 · commander 1 · engine 1 · threat 1 · lands 6\n")


def test_changes_twice_change_nothing():
    run("skills/sync/apply_changes.py")
    once = snapshot()
    out = run("skills/sync/apply_changes.py")
    assert out.stdout == ""
    assert snapshot() == once


def test_changes_rows_stay():
    before = read("changes.md")
    run("skills/sync/apply_changes.py")
    assert read("changes.md") == before


def test_sync_drops_landed_rows_but_unowned():
    landed = ["1 Zara, Tide Caller", "", "1 Deep Current", "1 Pearl Diver", ""]
    sync.drop_landed({"zara": landed})
    rows = [l for l in read("changes.md").splitlines() if l.startswith("| zara")]
    assert rows == ["| zara | Pearl Diver |  | unowned |"]


def changes(*rows):
    """changes.md holding only these zara rows, each (In, Out, Note)"""
    Path("changes.md").write_text("| Deck | In | Out | Note |\n|---|---|---|---|\n"
                                  + "".join(f"| zara | {i} | {o} | {n} |\n" for i, o, n in rows))


def test_to_copies_sets_a_card_up_in_place_and_adds_an_absent_one():
    changes(("Island", "", "to 6 copies"), ("Tidepool Ruins", "", "to 2 copies"))
    out = run("skills/sync/apply_changes.py")
    assert out.stdout == "zara: in Island (6); Tidepool Ruins (2) | out - | 17 (short 83)\n"
    assert "6 Island\n" in read(LIST) and read(LIST).splitlines()[-1] == "2 Tidepool Ruins"
    lands = read("output/decks/zara/lands.md")
    assert "| Island (6) | 6 | land | Basic |" in lands and "Island (4)" not in lands
    assert "| Tidepool Ruins (2) | - | - | Untapped utility land |" in lands
    assert "Tidepool Ruins | - | - | Untapped utility land | No" not in lands   # left the Adds table
    assert lands.endswith("5-7: 8 / 4 or below: 0, mean 6.0 (by card copy), 3 scorers.\n")
    assert read("output/decks/zara/nonlands.md").endswith("lands 8\n")


def test_to_copies_sets_a_card_down_and_to_zero():
    changes(("", "Island", "to 2 copies"), ("", "Misty Cove", "to 0 copies"))
    out = run("skills/sync/apply_changes.py")
    assert out.stdout == "zara: in - | out Island; Misty Cove | 10 (short 90)\n"
    assert "2 Island\n" in read(LIST) and "Misty Cove" not in read(LIST)
    lands = read("output/decks/zara/lands.md")
    assert "| Island (2) | 6 | land | Basic |" in lands and "Misty Cove" not in lands   # its Cards and Cuts rows
    assert lands.endswith("5-7: 3 / 4 or below: 0, mean 6.3 (by card copy), 3 scorers.\n")
    assert read("output/decks/zara/nonlands.md").endswith("lands 3\n")


def test_to_copies_twice_changes_nothing():
    changes(("Island", "", "to 6 copies"), ("", "Misty Cove", "to 0 copies"), ("Tidepool Ruins", "", "to 2 copies"))
    run("skills/sync/apply_changes.py")
    once = snapshot()
    assert run("skills/sync/apply_changes.py").stdout == ""
    assert snapshot() == once


def test_to_copies_on_a_row_naming_two_cards_is_skipped():
    changes(("Island", "Sol Ring", "to 3 copies"))
    before = snapshot()
    out = run("skills/sync/apply_changes.py")
    assert out.stdout == 'skip zara: Island for Sol Ring, "to 3 copies" sets one card\n'
    assert snapshot() == before


@pytest.mark.parametrize("islands, count", [(91, "100"), (90, "99 (short 1)"), (93, "102 (over 2)")])
def test_changes_line_ends_with_the_deck_count(islands, count):
    changes(("Island", "", f"to {islands} copies"))
    assert run("skills/sync/apply_changes.py").stdout == f"zara: in Island ({islands}) | out - | {count}\n"


def test_changes_count_leaves_out_the_sideboard():
    Path(LIST).write_text(read(LIST) + "\nSIDEBOARD:\n1 Spare Card\n")
    changes(("Island", "", "to 91 copies"))
    assert run("skills/sync/apply_changes.py").stdout == "zara: in Island (91) | out - | 100\n"


def test_sync_drops_a_to_copies_row_once_moxfield_shows_that_count():
    changes(("Island", "", "to 6 copies"), ("", "Misty Cove", "to 0 copies"), ("Forest", "", "to 2 copies"))
    sync.drop_landed({"zara": ["1 Zara, Tide Caller", "", "4 Island", "1 Forest", "", "SIDEBOARD:", "1 Forest", ""]})
    assert "| zara |  | Misty Cove | to 0 copies |" not in read("changes.md")
    assert "Island" in read("changes.md") and "Forest" in read("changes.md")
    sync.drop_landed({"zara": ["1 Zara, Tide Caller", "", "6 Island", "2 Forest", ""]})
    assert [l for l in read("changes.md").splitlines() if l.startswith("| zara")] == []


DECK = """1 Zara, Tide Caller

1 Brine Elemental
1 Coral Signet
4 Island
1 Sol Ring
"""
SIDE = "\nSIDEBOARD:\n1 Spare Card\n"
EXPORTS = {
    "moxfield": ("1 Zara, Tide Caller (ZTC) 1 *F*\n\n1 Brine Elemental (ZTC) 12\n1 Coral Signet (ZTC) 210\n"
                 "4 Island (ZTC) 300\n1 Sol Ring (C21) 263\n\nSIDEBOARD:\n1 Spare Card (ZTC) 21\n", True),
    "archidekt": ("1x Zara, Tide Caller (ztc) 1 [Commander{top}]\n1x Sol Ring (c21) 263 [Ramp]\n"
                  "4x Island (ztc) 300 [Land]\n1x Brine Elemental (ztc) 12 *F* [Creature]\n"
                  "1x Coral Signet (ztc) 210 [Ramp]\n1x Pearl Diver (ztc) 20 [Maybeboard{noDeck}{noPrice},Creature]\n"
                  "1x Spare Card (ztc) 21 [Sideboard{noDeck}]\n", True),
    "mtgo": ("1 Brine Elemental\n1 Coral Signet\n4 Island\n1 Sol Ring\n\n1 Zara, Tide Caller\n", False),
    "arena": ("Commander\n1 Zara, Tide Caller (ZTC) 1\n\nDeck\n1 Brine Elemental (ZTC) 12\n1 Coral Signet (ZTC) 210\n"
              "4 Island (ZTC) 300\n1 Sol Ring (C21) 263\n\nSideboard\n1 Spare Card (ZTC) 21\n", True),
}


@pytest.mark.parametrize("shape", EXPORTS)
def test_import(shape):
    text, side = EXPORTS[shape]
    out = run("skills/sync/import.py", "imported", stdin=text)
    assert out.returncode == 0, out.stderr
    assert out.stdout == "imported: 8 cards, 1 of them commander" + (", 1 in the sideboard" if side else "") + "\n"
    assert read("output/decks/imported/list.txt") == DECK + (SIDE if side else "")


DECKS = {"data": [  # MTGJSON's DeckList.json
    {"name": "Creative Energy", "code": "M3C", "fileName": "CreativeEnergy_M3C", "type": "Commander Deck"},
    {"name": "Creative Energy Collector's Edition", "code": "M3C", "fileName": "CreativeEnergyCE_M3C", "type": "Commander Deck"},
    {"name": "Tidal Pull", "code": "ZTC", "fileName": "TidalPull_ZTC", "type": "Commander Deck"},
    {"name": "Tidal Pulse", "code": "ZTC", "fileName": "TidalPulse_ZTC", "type": "Commander Deck"},
    {"name": "Zara's Tide", "code": "ZTC", "fileName": "ZarasTide_ZTC", "type": "Commander Deck"},
    {"name": "Zara's Theme", "code": "ZTH", "fileName": "ZarasTheme_ZTH", "type": "Theme Deck"}]}
PRECON = {"data": {"name": "Zara's Tide", "commander": [{"name": "Zara, Tide Caller", "count": 1}],  # each printing apart
                   "mainBoard": [{"name": "Sol Ring", "count": 1}, {"name": "Island", "count": 3},
                                 {"name": "Brine Elemental", "count": 1}, {"name": "Island", "count": 1},
                                 {"name": "Coral Signet", "count": 1}], "sideBoard": []}}


def precon(monkeypatch, name):
    """import.py run on a precon name against MTGJSON's deck list and Zara's Tide; the deck files it asked for"""
    asked, imp = [], importlib.import_module("import")
    def get(url):
        if url == f"{net.MTGJSON}/DeckList.json": return json.dumps(DECKS).encode()
        asked.append(url); return json.dumps(PRECON).encode()
    monkeypatch.setattr(imp, "get", get)
    monkeypatch.setattr(sys, "argv", ["import.py", "tide", name])
    imp.main()
    return asked


@pytest.mark.parametrize("name", ["Zara's Tide", "zara's t", "ZARA"])
def test_import_a_precon_by_name_or_unique_prefix(monkeypatch, capsys, name):
    assert precon(monkeypatch, name) == [f"{net.MTGJSON}/decks/ZarasTide_ZTC.json"]
    assert read("output/decks/tide/list.txt") == DECK
    assert capsys.readouterr().out == "tide: 8 cards, 1 of them commander\n"


def test_import_a_precon_whose_name_begins_another(monkeypatch):
    assert precon(monkeypatch, "creative energy") == [f"{net.MTGJSON}/decks/CreativeEnergy_M3C.json"]


@pytest.mark.parametrize("name, said", [
    ("tidal", "several Commander precons named 'tidal'; candidates:\nTidal Pull (ZTC)\nTidal Pulse (ZTC)"),
    ("Zara's Theme", "no Commander precons named \"Zara's Theme\"; candidates:\nCreative Energy (M3C)\n"
                     "Creative Energy Collector's Edition (M3C)\nTidal Pull (ZTC)\nTidal Pulse (ZTC)\nZara's Tide (ZTC)")])
def test_an_ambiguous_or_unknown_precon_prints_the_candidates(monkeypatch, name, said):
    with pytest.raises(SystemExit) as out: precon(monkeypatch, name)
    assert str(out.value) == said
    assert not Path("output/decks/tide").exists()


def test_import_reports_what_it_cannot_parse():
    out = run("skills/sync/import.py", "imported", stdin="Sol Ring, but no count\n1 Sol Ring\n")
    assert out.stdout.splitlines()[1:] == ["no commander found: put it first, set apart by a blank line, and rerun",
                                          "not parsed: Sol Ring, but no count"]
    assert read("output/decks/imported/list.txt") == "1 Sol Ring\n"


def test_card_names():
    names = fetch_oracle.card_names()
    assert names == ["Brine Elemental", "Coral Signet", "Deep Current", "Island", "Kelp Weaver", "Misty Cove",
                     "Sol Ring", "Sunken Grotto", "Tidal Insight", "Tidepool Ruins", "Wave Breaker", "Zara, Tide Caller"]
    assert set(names) <= set(json.loads(read("output/data/oracle.json"))["cards"])


def test_a_failed_save_leaves_oracle_json(monkeypatch):
    before = read("output/data/oracle.json")
    def broken(path, text):
        path.write_text(text[:10])
        raise OSError("disk full")
    monkeypatch.setattr(fetch_oracle, "write", broken)
    with pytest.raises(OSError):
        fetch_oracle.save({"cards": {}})
    assert read("output/data/oracle.json") == before


UNBLOCK = "open moxfield.com in the browser pane, pass the check and rerun /sync"


def test_sync_adds_a_deck_and_leaves_blocked_and_stale_ones():
    old = {"created": "2024-01-01", "updated": "2024-02-01"}
    Path("moxfield.json").write_text(json.dumps({"user": "owner", "decks": {"z1": "zara", "b1": "blocked", "s1": "stale"},
                                                 "dates": {"z1": old, "s1": old, "gone": old}}))
    out = run("skills/sync/sync.py", str(MOX))
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == ["added: krakens (k1)", f"blocked: blocked (Cloudflare challenge); {UNBLOCK}",
                                       "not in the dump: stale", "zara: in Deep Current; Pearl Diver | out Wave Breaker | 14 (short 86)",
                                       "rescore: krakens", "rescore: zara",
                                       "not refreshed: blocked, stale (tokens.md left as it was)"]
    assert json.loads(read("moxfield.json")) == {"user": "owner", "decks": {"z1": "zara", "b1": "blocked", "s1": "stale",
                                                                          "k1": "krakens"}, "seen": ["b1", "k1", "s1", "z1"],
                                                 "dates": {"z1": {"created": "2025-01-01", "updated": "2025-06-01"}, "s1": old,
                                                           "k1": {"created": "2026-01-01", "updated": "2026-02-01"}}}
    assert read("output/decks/krakens/list.txt") == "1 Kraken Lord\n\n9 Island\n1 Sol Ring\n\nSIDEBOARD:\n1 Spare Card\n"
    assert not Path("output/decks/blocked").exists() and not Path("output/data/tokens.md").exists()


def test_sync_writes_tokens_once_every_deck_came_back():
    Path("moxfield.json").write_text(json.dumps({"user": "owner", "decks": {"z1": "zara"}}))
    assert run("skills/sync/sync.py", str(MOX)).returncode == 0
    assert read("output/data/tokens.md") == """# Tokens

| Token | P/T | Colors | Type | Decks |
|---|---|---|---|---|
| Treasure |  | - | Token Artifact — Treasure | krakens |
| Fish | 1/1 | U | Token Creature — Fish | krakens, zara |
"""
    again = run("skills/sync/sync.py", str(MOX))
    assert "rescore" not in again.stdout and "added" not in again.stdout


PLAIN = ["Brine Elemental", "Coral Signet", "Deep Current", "Island", "Kelp Weaver", "Misty Cove", "Sol Ring",
         "Sunken Grotto", "Tidal Insight", "Tidepool Ruins", "Wave Breaker", "Zara, Tide Caller"]
TIDE = {"name": "Rising Tide // Tidal Flats", "oracle_id": "tide", "type_line": "Instant // Land", "game_changer": True,
        "legalities": {"commander": "legal", "modern": "legal"}, "prices": {"usd": "1"},
        "card_faces": [{"name": "Rising Tide", "mana_cost": "{1}{U}", "type_line": "Instant", "artist": "-"},
                       {"name": "Tidal Flats", "type_line": "Land"}],
        "all_parts": [{"component": "token", "name": "Fish"}, {"component": "combo_piece", "name": "Rising Tide"}]}


TREE = [  # Scryfall's oracle tags bulk: each tag's direct taggings only, its parents by id
    {"id": "r", "label": "ramp", "type": "oracle", "parent_ids": [], "taggings": []},
    {"id": "p", "label": "mana producer", "type": "oracle", "parent_ids": ["r"], "taggings": []},
    {"id": "m", "label": "mana rock", "type": "oracle", "parent_ids": ["p"], "taggings": [{"oracle_id": "Sol Ring"}]},
    {"id": "x", "label": "removal", "type": "oracle", "parent_ids": None, "taggings": []},
    {"id": "s", "label": "spot removal", "type": "oracle", "parent_ids": ["x"], "taggings": [{"oracle_id": "wave"}]},
    {"id": "c", "label": "removal-creature", "type": "oracle", "parent_ids": ["s", "x"], "taggings": [{"oracle_id": "tide"}]}]
TAGS = gzip.compress("\n".join(map(json.dumps, TREE)).encode())
NOV = "2026-11-01T00:00:00.000+00:00"
INDEX = {"data": [{"type": "oracle_cards"}, {"type": "rulings", "jsonl_download_uri": "rulings"},
                  {"type": "oracle_tags", "updated_at": NOV, "jsonl_download_uri": "tags"}]}
ATOMIC = {"meta": {"version": "5.3.0+20261101"}, "data": {  # MTGJSON's atomic cards, one per face
    "Rising Tide // Tidal Flats": [{"faceName": f, "edhrecSaltiness": 0.5, "identifiers": {"scryfallOracleId": "tide"}}
                                   for f in ("Rising Tide", "Tidal Flats")],
    "Sol Ring": [{"edhrecSaltiness": 1.59, "identifiers": {"scryfallOracleId": "Sol Ring"}}],
    "Tidal Wave": [{"edhrecSaltiness": 0.2, "identifiers": {"scryfallOracleId": "wave"}}],
    "Island": [{"identifiers": {"scryfallOracleId": "Island"}}]}}


def mtgjson(version="5.3.0+20261101"):
    """MTGJSON's Meta.json naming version, and its atomic cards"""
    return {f"{net.MTGJSON}/Meta.json": json.dumps({"data": {"version": version}}).encode(),
            f"{net.MTGJSON}/AtomicCards.json.gz": gzip.compress(json.dumps(ATOMIC).encode())}


def scryfall(posts):
    """Scryfall's collection, bulk-data, rulings and oracle tags answers, and MTGJSON's. A double-faced card is found only by its front face, and
    Sign in Blood only when posted alone (in a batch it comes back as neither found nor not found)."""
    def get(url, body=None):
        if body:
            names = [i["name"] for i in body["identifiers"]]
            posts.append(names)
            card = lambda n: TIDE if n == "Rising Tide" else {"name": n, "oracle_id": n, "type_line": "Instant",
                                                               "legalities": {"commander": "legal"}}
            data = [card(n) for n in names if n in PLAIN + ["Rising Tide"] or names == ["Sign in Blood"]]
            lost = [{"name": n} for n in names if n not in PLAIN + ["Rising Tide", "Sign in Blood"]]
            return json.dumps({"data": data, "not_found": lost}).encode()
        if url.endswith("/bulk-data"): return json.dumps(INDEX).encode()
        if url == "tags": return TAGS
        if url.startswith(net.MTGJSON): return mtgjson()[url]
        assert url == "rulings"
        return gzip.compress(b'{"oracle_id": "tide", "published_at": "2024-02-01", "comment": "Second."}\n'
                             b'{"oracle_id": "tide", "published_at": "2023-01-01", "comment": "First."}\n')
    return get


def test_rebuild_retries_double_faced_cards_by_front_face_and_lone_names_alone(monkeypatch, capsys):
    with open(LIST, "a") as f: f.write("1 Rising Tide // Tidal Flats\n1 Sign in Blood\n1 Not A Card\n")
    posts = []
    monkeypatch.setattr(fetch_oracle, "get", scryfall(posts))
    fetch_oracle.rebuild()
    names = fetch_oracle.card_names()
    assert posts == [names, ["Rising Tide"], ["Not A Card"], ["Sign in Blood"]]
    assert capsys.readouterr().out == (f"{len(names)} requested, 14 saved; missing: ['Not A Card']\n"
                                       "game changers: ['Rising Tide // Tidal Flats']\n")
    cards = json.loads(read("output/data/oracle.json"))["cards"]
    assert sorted(cards) == sorted(PLAIN + ["Rising Tide // Tidal Flats", "Sign in Blood"])
    assert cards["Rising Tide // Tidal Flats"] == {
        "name": "Rising Tide // Tidal Flats", "oracle_id": "tide", "type_line": "Instant // Land", "game_changer": True,
        "legalities": {"commander": "legal"}, "related_tokens": ["Fish"], "rulings": ["First.", "Second."],
        "tags": ["removal", "removal-creature", "spot removal"], "salt": 0.5, "card_faces": [{"name": "Rising Tide", "mana_cost": "{1}{U}", "type_line": "Instant"},
                       {"name": "Tidal Flats", "type_line": "Land"}]}
    assert cards["Sol Ring"]["rulings"] == []
    assert cards["Sol Ring"]["tags"] == ["mana producer", "mana rock", "ramp"]
    assert cards["Island"]["tags"] == [] and "salt" not in cards["Island"]
    assert cards["Sol Ring"]["salt"] == 1.59


def test_tags_download_again_only_when_the_index_shows_a_newer_file(monkeypatch):
    got = []
    monkeypatch.setattr(fetch_oracle, "get", lambda url: got.append(url) or TAGS)
    index = lambda when: {"oracle_tags": {"updated_at": when, "jsonl_download_uri": "tags"}}
    assert fetch_oracle.tags() == {}
    fetch_oracle.tags(index(NOV))
    assert fetch_oracle.tags(index(NOV)) == fetch_oracle.tags() == {
        "Sol Ring": ["mana producer", "mana rock", "ramp"], "wave": ["removal", "spot removal"],
        "tide": ["removal", "removal-creature", "spot removal"]}
    assert got == ["tags"]
    fetch_oracle.tags(index("2026-11-02T00:00:00.000+00:00"))
    assert got == ["tags", "tags"]


def test_atomic_cards_download_again_only_when_mtgjson_names_a_new_version(monkeypatch):
    got, answers = [], mtgjson()
    monkeypatch.setattr(fetch_oracle, "get", lambda url: got.append(url) or answers[url])
    assert fetch_oracle.salts() == {}
    assert fetch_oracle.salts(fresh=True) == fetch_oracle.salts(fresh=True) == fetch_oracle.salts() == {
        "tide": 0.5, "Sol Ring": 1.59, "wave": 0.2}
    meta, atomic = answers
    assert got == [meta, atomic, meta]
    answers.update(mtgjson("5.3.0+20261102"))
    fetch_oracle.salts(fresh=True)
    assert got == [meta, atomic, meta, meta, atomic]


def test_add_fetches_only_the_names_oracle_json_lacks(monkeypatch):
    before = json.loads(read("output/data/oracle.json"))["cards"]
    fetch_oracle.TAGS.write_bytes(TAGS)
    fetch_oracle.ATOMIC.write_bytes(mtgjson()[f"{net.MTGJSON}/AtomicCards.json.gz"])
    wave = {"name": "Tidal Wave", "oracle_id": "wave", "type_line": "Sorcery", "legalities": {"commander": "legal"},
            "rulings_uri": "wave-rulings"}
    asked = []
    def found(url):
        asked.append(url)
        return wave if url == project.NAMED + "Tidal%20Wave" else None
    monkeypatch.setattr(project, "found", found)
    monkeypatch.setattr(project, "get", lambda url: b'{"data": [{"comment": "It waves."}]}' if url == "wave-rulings" else None)
    assert fetch_oracle.add(["sol ring", "Tidal Wave", "Nothing Card"]) == ["Nothing Card"]
    assert asked == [project.NAMED + "Tidal%20Wave", project.NAMED + "Nothing%20Card"]
    assert json.loads(read("output/data/oracle.json"))["cards"] == {**before, "Tidal Wave": {
        "name": "Tidal Wave", "oracle_id": "wave", "type_line": "Sorcery", "legalities": {"commander": "legal"},
        "related_tokens": [], "rulings": ["It waves."], "tags": ["removal", "spot removal"], "salt": 0.2}}


def test_plan_check_prints_the_plan_cards_not_in_the_list():
    assert run("skills/sync/plan_check.py", "zara").stdout == ""
    Path("output/decks/zara/plan.md").write_text(
        "# Zara, Tide Caller: plan\n\n"
        "- **Win:** Loop: Zara, Tide Caller + Mr. Missing + Kelp Weaver. Draws the table out.\n"
        "- **Win:** Beats: Zara, Tide Caller + big fish (Brine Elemental; Wave Breaker; Lost Fish) + mana (Sol Ring;"
        " Ghost Signet). Swings for lethal (twice).\n"
        "- **Commander:** draws a card on every spell.\n"
        "- **Not cast:** Brine Elemental; Nowhere Card\n"
        "- **Mana:** excluded\n")
    out = run("skills/sync/plan_check.py", "zara", "nodeck")
    assert out.returncode == 0, out.stderr
    assert out.stdout == ("zara: Mr. Missing is not in list.txt\nzara: Lost Fish is not in list.txt\n"
                          "zara: Ghost Signet is not in list.txt\nzara: Nowhere Card is not in list.txt\n")


def test_plan_check_checks_a_draft_outside_output_against_the_slugs_list(tmp_path):
    draft = tmp_path / "zara-plan.md"
    draft.write_text("# Zara, Tide Caller: plan\n\n"
                     "- **Win:** Out-card: Zara, Tide Caller + spells (Tidal Insight; Lost Fish). Draws the table out.\n"
                     "- **Not cast:** Nowhere Card\n")
    before = snapshot()
    out = run("skills/sync/plan_check.py", "--plan", str(draft), "zara")
    assert out.returncode == 0, out.stderr
    assert out.stdout == "zara: Lost Fish is not in list.txt\nzara: Nowhere Card is not in list.txt\n"
    assert run("skills/sync/plan_check.py", "zara").stdout == "" and snapshot() == before
    assert run("skills/sync/plan_check.py", "--plan", str(draft)).returncode == 1
