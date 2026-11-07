from pathlib import Path
import pytest
from PIL import Image
from conftest import run, read, snapshot
import project, sheet as script

ADDS = """# Zara, Tide Caller: top adds (2026-11-02)
Built 2025-01-01, last edited 2025-06-01.

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


def research(adds=ADDS):
    Path("run").mkdir(exist_ok=True)
    Path("run/zara-adds.md").write_text(adds)
    Path("run/zara-cuts.md").write_text(CUTS)
    return run("skills/upgrades/apply.py", "run", "zara")


def test_apply_routes_keeps_and_drops():
    out = research()
    assert out.returncode == 0, out.stderr
    assert out.stdout.splitlines() == ["zara: restricted, not added: Tundra",
                                       "zara: above the $20 budget, not added: Mana Vault",
                                       "zara: Adds and Cuts written to output/decks/zara/nonlands.md and lands.md"]
    nonlands, lands = read("output/decks/zara/nonlands.md"), read("output/decks/zara/lands.md")
    assert """
| Card | Score | Role | Note | New | ~Price |
|---|---|---|---|---|---|
| Deep Current | 7 | engine | A card on every spell, stacks with Zara | Yes | $1.50 |
| Pearl Diver | - | - | Cheap scry body | Yes | $0.25 |
| Rising Tide // Tidal Flats | - | - | Draw now or a land later | No | $0.80 |
| Odd Relic | - | - | Price unknown | No | n/a |

## Cuts
| Card | Score | Why it underperforms here |
|---|---|---|
| Wave Breaker | 3 | Off-colour aggro |
""" in nonlands
    assert """
| Tidepool Ruins | - | - | Utility land | No | $0.40 |

## Cuts
| Card | Score | Why it underperforms here |
|---|---|---|
| Misty Cove | 5 | Tapped land |
""" in lands
    assert "Tundra" not in nonlands + lands and "Mana Vault" not in nonlands + lands


def test_apply_keeps_an_unknown_new_since_built():
    assert research(ADDS.replace("| Yes |", "| - |")).returncode == 0
    nonlands = read("output/decks/zara/nonlands.md")
    assert "| Deep Current | 7 | engine | A card on every spell, stacks with Zara | - | $1.50 |" in nonlands
    assert "| Pearl Diver | - | - | Cheap scry body | Yes | $0.25 |" in nonlands
    assert "| Odd Relic | - | - | Price unknown | No | n/a |" in nonlands


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
    def offline(url): raise AssertionError(f"fetched {url}")
    monkeypatch.setattr(project, "get", offline)
    monkeypatch.setattr(project, "found", offline)
    return script


def test_grid_choice(sheet):
    band = lambda n: [("Band", [("card", "5")] * n)]
    assert [sheet.columns(band(n)) for n in (1, 3, 4, 20)] == [1, 3, 2, 5]
    assert sheet.size(band(4), 2) == (2 * sheet.W + sheet.GAP, sheet.HEAD + 2 * (sheet.H + sheet.HEAD) + sheet.GAP)


def test_bands_in_order(sheet):
    assert sheet.bands("zara") == [("Nonland adds", [("Deep Current", "7")]), ("Nonland cuts", [("Wave Breaker", "3")]),
                                   ("Land adds", [("Tidepool Ruins", "-")]), ("Land cuts", [("Misty Cove", "5")])]


def test_empty_band_left_out(sheet):
    lands = Path("output/decks/zara/lands.md")
    lands.write_text(lands.read_text().replace("| Misty Cove | 5 | Enters tapped for no gain |\n", ""))
    assert [head for head, _ in sheet.bands("zara")] == ["Nonland adds", "Nonland cuts", "Land adds"]


def test_an_image_comes_from_the_cache_or_is_fetched_into_it(sheet, monkeypatch):
    Path("output/data/images").mkdir()
    Image.new("RGB", (10, 14), "red").save("output/data/images/Deep Current.jpg")
    img = sheet.image("Deep Current")
    assert (img.mode, img.size) == ("RGB", (sheet.W, sheet.H)) and img.getpixel((sheet.W // 2, sheet.H // 2))[0] > 200
    blue = Path("blue.jpg")
    Image.new("RGB", (10, 14), "blue").save(blue)
    face = {"data": [{"card_faces": [{"image_uris": {"normal": "front.jpg"}}, {"image_uris": {"normal": "back.jpg"}}]}]}
    monkeypatch.setattr(project, "found", lambda url: face if "Rising" in url else None)
    monkeypatch.setattr(project, "get", {"front.jpg": blue.read_bytes()}.__getitem__)
    assert sheet.image("Rising Tide").getpixel((sheet.W // 2, sheet.H // 2))[2] > 200
    assert Path("output/data/images/Rising Tide.jpg").read_bytes() == blue.read_bytes()
    assert sheet.image("No Such Card") is None


def test_band_layout_with_stub_images(sheet, monkeypatch, capsys):
    colour = {"A": "red", "B": "green", "C": "blue", "D": "yellow"}
    monkeypatch.setattr(sheet, "image", lambda n: Image.new("RGB", (sheet.W, sheet.H), colour[n]) if n in colour else None)
    bands = [("First", [("A", "7"), ("B", "-"), ("C", "10"), ("D", "4"), ("Missing", "6"), ("A", "7")]),
             ("Second", [("B", "3")])]
    out = sheet.sheet(bands)
    W, H, GAP, HEAD = sheet.W, sheet.H, sheet.GAP, sheet.HEAD
    assert sheet.columns(bands) == 3
    assert out.size == (3 * W + 2 * GAP, 2 * HEAD + 3 * (H + HEAD) + 2 * GAP)
    at = lambda col, y: out.getpixel((col * (W + GAP) + W // 2, y + H // 2))
    row2, second = HEAD + H + HEAD + GAP, HEAD + 2 * (H + HEAD + GAP) + HEAD
    assert [at(c, HEAD) for c in range(3)] == [(255, 0, 0), (0, 128, 0), (0, 0, 255)]
    assert [at(c, row2) for c in range(3)] == [(255, 255, 0), (255, 255, 255), (255, 0, 0)]
    assert [at(c, second) for c in range(3)] == [(0, 128, 0), (255, 255, 255), (255, 255, 255)]
    label = lambda col, y: out.crop((col * (W + GAP), y + H, col * (W + GAP) + W, y + H + HEAD))
    inked = lambda col, y: label(col, y).convert("L").getextrema()[0] < 100
    assert [inked(c, HEAD) for c in range(3)] == [True] * 3 and [inked(c, row2) for c in range(3)] == [True] * 3
    assert [inked(c, second) for c in range(3)] == [True, False, False]
    assert label(2, row2).tobytes() == label(0, HEAD).tobytes() != label(1, HEAD).tobytes()  # 7, 7, then B's -
    assert "not on Scryfall, left blank: Missing" in capsys.readouterr().out


def test_images_false_draws_nothing():
    Path("settings.json").write_text('{"images": false}')
    out = run("skills/upgrades/sheet.py", "zara")
    assert (out.returncode, out.stdout) == (0, "images is false in settings.json: no sheet drawn\n")
    assert not Path("output/decks/zara/changes.png").exists() and not Path("output/data/images").exists()


def test_every_add_scored_by_name_reaches_the_sheet(sheet):
    """upgrades step 3: each add, as tables.py prints it, scored as a candidate and merged by name, shows its score"""
    research()
    names = run("lib/tables.py", "zara").stdout.splitlines()
    assert names == ["Deep Current", "Pearl Diver", "Rising Tide // Tidal Flats", "Odd Relic", "Tidepool Ruins"]
    score = dict(zip(names, ("8", "6", "5", "3", "7")))
    for letter in "AB":
        Path(f"run/work-zara-{letter}").mkdir()
        Path(f"run/work-zara-{letter}/zara.md").write_text("# Zara, Tide Caller: fit scores\n\n## Adds\n"
            "| Card | Score | Role | Note |\n|---|---|---|---|\n" + "".join(f"| {n} | {s} | draw | fits |\n" for n, s in score.items()))
    out = run("skills/score-cards/merge.py", "run", "zara", *names)
    assert out.returncode == 0, out.stderr
    for k in project.KINDS: Path(f"output/decks/zara/{k}.md").write_text(read(f"run/merged/zara/{k}.md"))
    assert dict(sheet.bands("zara")) == {
        "Nonland adds": [("Deep Current", "8"), ("Pearl Diver", "6"), ("Rising Tide", "5"), ("Odd Relic", "3")],
        "Nonland cuts": [("Wave Breaker", "3")], "Land adds": [("Tidepool Ruins", "7")], "Land cuts": [("Misty Cove", "5")]}
    assert "| Pearl Diver | 6 | draw | fits | Yes | $0.25 |" in read("output/decks/zara/nonlands.md")
