import json
from pathlib import Path
from conftest import read
import collection, fetch_oracle, project

DECK = ["Brine Elemental", "Coral Signet", "Island", "Kelp Weaver", "Misty Cove", "Sol Ring", "Sunken Grotto",
        "Tidal Insight", "Wave Breaker", "Zara, Tide Caller"]  # the fixture deck zara's cards, sorted


def test_the_seed_adds_each_missing_deck_card_at_one_copy_and_keeps_rows():
    Path("collection.md").write_text("# Collection\n\nMine.\n\n| Card | Copies |\n|---|---|\n| sol ring | 3 |\n"
                                      "| Glacial Wall | 2 |\n\nTrades pending.\n")
    assert collection.seed() == 9
    assert read("collection.md") == ("# Collection\n\nMine.\n\n| Card | Copies |\n|---|---|\n| sol ring | 3 |\n"
                                     "| Glacial Wall | 2 |\n" + "".join(f"| {n} | 1 |\n" for n in DECK if n != "Sol Ring")
                                     + "\nTrades pending.\n")
    assert collection.seed() == 0


def test_the_seed_writes_the_collection_when_there_is_none():
    assert collection.seed() == 10
    assert read("collection.md") == "# Collection\n\n| Card | Copies |\n|---|---|\n" + "".join(f"| {n} | 1 |\n" for n in DECK)


def test_the_cache_fetches_only_the_images_and_oracle_entries_missing(monkeypatch):
    Path("output/data/images").mkdir()
    for n in DECK[1:]: Path(f"output/data/images/{n}.jpg").write_bytes(b"cached")
    wall = {"name": "Glacial Wall", "oracle_id": "wall", "legalities": {"commander": "legal"}, "rulings_uri": "rulings"}
    asked = []
    def found(url):
        asked.append(url)
        if url.startswith(project.SEARCH): return None if "Nothing" in url else {"data": [{"image_uris": {"normal": "jpg"}}]}
        return wall if url == project.NAMED + "Glacial%20Wall" else None
    monkeypatch.setattr(project, "found", found)
    monkeypatch.setattr(project, "get", {"jpg": b"image", "rulings": b'{"data": []}'}.__getitem__)
    names = DECK + ["Glacial Wall", "Nothing Card"]
    assert collection.cache(names) == (2, 1, ["Nothing Card"])
    assert [u.split("?")[0].rsplit("/", 1)[-1] for u in asked] == ["search"] * 3 + ["named"] * 2
    assert all(n in u for n, u in zip(["Brine", "Glacial", "Nothing", "Glacial", "Nothing"], asked))
    assert Path("output/data/images/Brine Elemental.jpg").read_bytes() == b"image"
    assert "Glacial Wall" in json.loads(read("output/data/oracle.json"))["cards"]
    asked.clear()
    assert collection.cache(names) == (0, 0, ["Nothing Card"]) and len(asked) == 2  # the card Scryfall lacks, asked again


def test_images_false_fetches_no_image(monkeypatch):
    Path("settings.json").write_text('{"images": false}')
    def offline(url): raise AssertionError(f"fetched {url}")
    monkeypatch.setattr(project, "found", offline)
    assert collection.cache(DECK) == (0, 0, [])
    assert not Path("output/data/images").exists()


def test_rebuild_keeps_the_collections_cards():
    Path("collection.md").write_text("| Card | Copies |\n|---|---|\n| Glacial Wall | 2 |\n")
    assert "Glacial Wall" in fetch_oracle.card_names()
