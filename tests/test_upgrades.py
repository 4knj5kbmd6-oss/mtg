from pathlib import Path
import pytest
from PIL import Image
from conftest import run, load, read, snapshot

ADDS = """# Zara, Tide Caller: top adds (2026-11-02)
Built 2025-01-01, last edited 2025-06-01, bracket 2.

| # | Add | New since built? | Why | ~Price |
|---|---|---|---|---|
| 1 | Deep Current | Yes | Card on every spell | $1.50 |
| 2 | Pearl Diver | Yes, 2026 | Cheap scry body | $0.25 |
| 3 | Tundra | No | Dual land | $500.00 |
| 4 | Rising Tide // Tidal Flats | No | Draw now or a land later | $0.80 |
| 5 | Mana Vault | No | Fast mana | $45.00 |
| 6 | Odd Relic | No | Price unknown | n/a |
| 7 | Tidepool Ruins | No | Utility land | $0.40 |
"""
CUTS = """# Zara, Tide Caller: top cuts (2026-11-02)

| # | Cut | Why it underperforms here |
|---|---|---|
| 1 | Wave Breaker | Off-colour aggro |
| 2 | Misty Cove | Tapped land |
"""


def research():
    Path("run").mkdir(exist_ok=True)
    Path("run/zara-adds.md").write_text(ADDS)
    Path("run/zara-cuts.md").write_text(CUTS)
    return run("upgrades/apply.py", "run", "zara")


def test_apply_routes_keeps_and_drops():
    out = research()
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == ["zara: restricted, not added: Tundra",
                                       "zara: above the $20 budget, not added: Mana Vault",
                                       "zara: Adds and Cuts written to output/decks/zara/nonlands.md and lands.md"]
    nonlands, lands = read("output/decks/zara/nonlands.md"), read("output/decks/zara/lands.md")
    assert """
| Card | Score | Note | New | ~Price |
|---|---|---|---|---|
| Deep Current | 7 | A card on every spell, stacks with Zara | Yes | $1.50 |
| Pearl Diver | - | Cheap scry body | Yes | $0.25 |
| Rising Tide // Tidal Flats | - | Draw now or a land later | No | $0.80 |
| Odd Relic | - | Price unknown | No | n/a |

## Cuts
| Card | Score | Why it underperforms here |
|---|---|---|
| Wave Breaker | 3 | Off-colour aggro |
""" in nonlands
    assert """
| Tidepool Ruins | - | Utility land | No | $0.40 |

## Cuts
| Card | Score | Why it underperforms here |
|---|---|---|
| Misty Cove | 5 | Tapped land |
""" in lands
    assert "Tundra" not in nonlands + lands and "Mana Vault" not in nonlands + lands


def test_apply_leaves_cards_and_shape():
    before = read("output/decks/zara/nonlands.md")
    research()
    after = read("output/decks/zara/nonlands.md")
    assert after.split("## Adds")[0] == before.split("## Adds")[0]
    assert after.split("## Shape")[1] == before.split("## Shape")[1]


def test_apply_twice_is_byte_identical():
    research()
    once = snapshot()
    research()
    assert snapshot() == once


@pytest.fixture
def sheet(monkeypatch):
    """sheet.py with fetching disabled"""
    module = load("upgrades/sheet.py")
    def offline(url): raise AssertionError(f"fetched {url}")
    monkeypatch.setattr(module, "get", offline)
    monkeypatch.setattr(module, "found", offline)
    return module


def test_grid_choice(sheet):
    band = lambda n: [("Band", ["card"] * n)]
    assert [sheet.columns(band(n)) for n in (1, 3, 4, 20)] == [1, 2, 2, 5]
    assert sheet.size(band(4), 2) == (2 * sheet.W + sheet.GAP, sheet.HEAD + 2 * sheet.H + sheet.GAP)


def test_bands_in_order(sheet):
    assert sheet.bands("zara") == [("Nonland adds", ["Deep Current"]), ("Nonland cuts", ["Wave Breaker"]),
                                   ("Land adds", ["Tidepool Ruins"]), ("Land cuts", ["Misty Cove"])]


def test_empty_band_left_out(sheet):
    lands = Path("output/decks/zara/lands.md")
    lands.write_text(lands.read_text().replace("| Misty Cove | 5 | Enters tapped for no gain |\n", ""))
    assert [head for head, _ in sheet.bands("zara")] == ["Nonland adds", "Nonland cuts", "Land adds"]


def test_band_layout_with_stub_images(sheet, monkeypatch, capsys):
    colour = {"A": "red", "B": "green", "C": "blue", "D": "yellow"}
    monkeypatch.setattr(sheet, "image", lambda n: Image.new("RGB", (sheet.W, sheet.H), colour[n]) if n in colour else None)
    bands = [("First", ["A", "B", "C", "D", "Missing", "A"]), ("Second", ["B"])]
    out = sheet.sheet(bands)
    W, H, GAP, HEAD = sheet.W, sheet.H, sheet.GAP, sheet.HEAD
    assert sheet.columns(bands) == 3
    assert out.size == (3 * W + 2 * GAP, 2 * HEAD + 3 * H + 2 * GAP)
    at = lambda col, y: out.getpixel((col * (W + GAP) + W // 2, y + H // 2))
    row2, second = HEAD + H + GAP, HEAD + 2 * (H + GAP) + HEAD
    assert [at(c, HEAD) for c in range(3)] == [(255, 0, 0), (0, 128, 0), (0, 0, 255)]
    assert [at(c, row2) for c in range(3)] == [(255, 255, 0), (255, 255, 255), (255, 0, 0)]
    assert [at(c, second) for c in range(3)] == [(0, 128, 0), (255, 255, 255), (255, 255, 255)]
    assert "not on Scryfall, left blank: Missing" in capsys.readouterr().out
