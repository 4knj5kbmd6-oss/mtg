import json
import pytest
from conftest import run, read, snapshot
import fetch_oracle, sync

LIST = "output/decks/zara/list.txt"


def test_changes_in_and_out():
    out = run("skills/sync/apply_changes.py")
    assert out.returncode == 0, out.stderr
    assert out.stdout == "zara: in Deep Current; Pearl Diver | out Wave Breaker\n"
    assert read(LIST).splitlines()[-3:] == ["1 Tidal Insight", "1 Deep Current", "1 Pearl Diver"]
    assert "Wave Breaker" not in read(LIST)
    nonlands = read("output/decks/zara/nonlands.md")
    assert "| Deep Current | 7 | A card on every spell, stacks with Zara |\n| Kelp Weaver |" in nonlands
    assert "Deep Current | 7 | A card on every spell, stacks with Zara | Yes" not in nonlands   # left the Adds table
    assert "Wave Breaker" not in nonlands
    assert nonlands.endswith("10: 1 / 8-9: 1 / 5-7: 4 / 4 or below: 1, mean 6.7 (by card copy), 3 scorers.\n")


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
