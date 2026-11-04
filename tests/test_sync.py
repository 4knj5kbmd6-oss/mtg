import gzip, json
from pathlib import Path
import pytest
from conftest import ROOT, run, read, snapshot
import fetch_oracle, project, sync

LIST = "output/decks/zara/list.txt"
MOX = ROOT / "tests" / "moxfield" / "mox.json"  # fetch.js's answer: Zara, a new deck, two decks sync skips, a blocked one


def test_changes_in_and_out():
    out = run("skills/sync/apply_changes.py")
    assert out.returncode == 0, out.stderr
    assert out.stdout == "zara: in Deep Current; Pearl Diver | out Wave Breaker\n"
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
                                       "not in the dump: stale", "zara: in Deep Current; Pearl Diver | out Wave Breaker",
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


def scryfall(posts):
    """Scryfall's collection, bulk-data and rulings answers. A double-faced card is found only by its front face, and
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
        if url.endswith("/bulk-data"):
            return json.dumps({"data": [{"type": "oracle_cards"}, {"type": "rulings", "jsonl_download_uri": "rulings"}]}).encode()
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
        "card_faces": [{"name": "Rising Tide", "mana_cost": "{1}{U}", "type_line": "Instant"},
                       {"name": "Tidal Flats", "type_line": "Land"}]}
    assert cards["Sol Ring"]["rulings"] == []


def test_add_fetches_only_the_names_oracle_json_lacks(monkeypatch):
    before = json.loads(read("output/data/oracle.json"))["cards"]
    wave = {"name": "Tidal Wave", "type_line": "Sorcery", "legalities": {"commander": "legal"}, "rulings_uri": "wave-rulings"}
    asked = []
    def found(url):
        asked.append(url)
        return wave if url == project.NAMED + "Tidal%20Wave" else None
    monkeypatch.setattr(project, "found", found)
    monkeypatch.setattr(project, "get", lambda url: b'{"data": [{"comment": "It waves."}]}' if url == "wave-rulings" else None)
    assert fetch_oracle.add(["sol ring", "Tidal Wave", "Nothing Card"]) == ["Nothing Card"]
    assert asked == [project.NAMED + "Tidal%20Wave", project.NAMED + "Nothing%20Card"]
    assert json.loads(read("output/data/oracle.json"))["cards"] == {**before, "Tidal Wave": {
        "name": "Tidal Wave", "type_line": "Sorcery", "legalities": {"commander": "legal"}, "related_tokens": [],
        "rulings": ["It waves."]}}
