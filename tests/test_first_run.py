"""A fresh project, an empty folder with no output/, through its first /sync, import, single-card fetch and /judge, every server
answered by a stub."""
import gzip, importlib, json, sys
from pathlib import Path
import pytest
from conftest import read
import fetch_oracle, fetch_rules, net, project, sync

DECK = {"name": "Zara", "created": "2025-01-01T00:00:00Z", "updated": "2025-06-01T00:00:00Z",
        "commanders": ["1 Zara, Tide Caller"], "mainboard": ["1 Sol Ring"], "sideboard": [],
        "tokens": [{"name": "Fish", "colors": ["U"], "pt": "1/1", "type": "Token Creature — Fish", "text": ""}]}
RULES = "https://media.wizards.com/2025/downloads/MagicCompRules 20250101.txt"


@pytest.fixture(autouse=True)
def empty(tmp_path, monkeypatch):
    (tmp_path / "fresh").mkdir()
    monkeypatch.chdir(tmp_path / "fresh")


def scryfall(url, body=None):
    """Scryfall's collection answer for every name posted, its bulk-data list, one ruling and no tags; MTGJSON's version
    and no atomic cards"""
    if body: return json.dumps({"data": [{"name": i["name"], "oracle_id": i["name"], "type_line": "Creature",
                                          "legalities": {"commander": "legal"}} for i in body["identifiers"]]}).encode()
    if url.endswith("/bulk-data"): return json.dumps({"data": [{"type": "rulings", "jsonl_download_uri": "rulings"},
        {"type": "oracle_tags", "updated_at": "2026-11-01T00:00:00.000+00:00", "jsonl_download_uri": "tags"}]}).encode()
    if url == "tags": return gzip.compress(b"")
    if url == f"{net.MTGJSON}/Meta.json": return b'{"data": {"version": "5.3.0"}}'
    if url == f"{net.MTGJSON}/AtomicCards.json.gz": return gzip.compress(b'{"meta": {"version": "5.3.0"}, "data": {}}')
    return gzip.compress(b'{"oracle_id": "Sol Ring", "published_at": "2020-01-01", "comment": "Taps for two."}\n')


def oracle(monkeypatch):
    monkeypatch.setattr(fetch_oracle, "get", scryfall)
    fetch_oracle.rebuild()
    return json.loads(read("output/data/oracle.json"))["cards"]


def test_first_sync_writes_the_list_tokens_and_oracle(monkeypatch):
    listing = [{"publicId": "z1", "name": "Zara", "format": "commander", "visibility": "public"}]
    Path("mox.json").write_text(json.dumps({"user": "owner", "listing": listing, "decks": {"z1": DECK}}))
    monkeypatch.setattr(sys, "argv", ["sync.py", "mox.json"])
    sync.main()
    assert read("output/decks/zara/list.txt") == "1 Zara, Tide Caller\n\n1 Sol Ring\n"
    assert "| Fish | 1/1 | U | Token Creature — Fish | zara |" in read("output/data/tokens.md")
    assert oracle(monkeypatch)["Sol Ring"]["rulings"] == ["Taps for two."]


def test_first_import_writes_the_list_and_oracle(monkeypatch):
    Path("deck.txt").write_text("1 Zara, Tide Caller\n\n1 Sol Ring\n")
    monkeypatch.setattr(sys, "argv", ["import.py", "zara", "deck.txt"])
    importlib.import_module("import").main()
    assert read("output/decks/zara/list.txt") == "1 Zara, Tide Caller\n\n1 Sol Ring\n"
    assert sorted(oracle(monkeypatch)) == ["Sol Ring", "Zara, Tide Caller"]


def test_first_single_card_fetch_writes_oracle(monkeypatch):
    ring = {"name": "Sol Ring", "type_line": "Artifact", "legalities": {"commander": "legal"}, "rulings_uri": "ring-rulings"}
    monkeypatch.setattr(project, "found", lambda url: ring if url == project.NAMED + "Sol%20Ring" else None)
    monkeypatch.setattr(project, "get", lambda url: b'{"data": [{"comment": "Taps for two."}]}')
    assert fetch_oracle.add(["Sol Ring"]) == []
    assert json.loads(read("output/data/oracle.json")) == {"cards": {"Sol Ring": {
        "name": "Sol Ring", "type_line": "Artifact", "legalities": {"commander": "legal"}, "related_tokens": [],
        "rulings": ["Taps for two."], "tags": []}}}


def test_first_judge_writes_the_rules(monkeypatch, capsys):
    pages = {fetch_rules.PAGE: f'<a href="{RULES}">TXT</a>'.encode(),
             RULES.replace(" ", "%20"): b"These rules are effective as of January 1, 2025.\r\n"}
    monkeypatch.setattr(fetch_rules, "get", pages.__getitem__)
    fetch_rules.main()
    assert read("output/data/rules.txt") == ("Source: https://media.wizards.com/2025/downloads/MagicCompRules%2020250101.txt\n"
                                             "These rules are effective as of January 1, 2025.\n")
    assert capsys.readouterr().out == "Comprehensive Rules effective January 1, 2025 (fetched)\n"
