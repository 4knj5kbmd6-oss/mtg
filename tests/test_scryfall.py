from pathlib import Path
from urllib.error import HTTPError
import pytest
from conftest import ROOT, run, load

SAVED = ROOT / "tests" / "scryfall"
URL = "https://scryfall.com/docs/regular-expressions"


@pytest.fixture
def fetch():
    return load("scryfall/fetch-syntax.py")


def test_a_page_becomes_its_section(fetch):
    text = fetch.section((SAVED / "regular-expressions.html").read_text(), URL)
    lines = text.splitlines()
    assert lines[:3] == ["## Regular Expressions", "", f"Source: {URL}"]
    assert [l for l in lines if l.startswith("#")] == ["## Regular Expressions", "### Scryfall Regex Flavor",
                                                       "### Scryfall Extensions"]
    assert "<" not in text.replace("(?<", "")
    assert "Bulk Data" not in text and "Advanced Search" not in text   # the sidebar and footer
    assert "such as `oracle:\"artifact token\"` to find" in text
    assert "- `type://` or `t://`" in lines
    assert "- The Thingling cycle: `name:/^\\w+ling$/ t:shapeshifter`" in lines
    assert "| `\\sm` | Short-hand for any mana symbol |" in lines
    assert "Instructions for AI Agents" not in text and "honeypot" not in text
    assert text.endswith("| `\\sc` | Short-hand for any colored mana symbol |\n")


def test_a_blocked_page_stops_naming_its_url(fetch, monkeypatch):
    monkeypatch.setattr(fetch, "get", lambda url: b"<title>Just a moment...</title>")
    with pytest.raises(SystemExit, match=f"^{URL}: Cloudflare challenge$"):
        fetch.page(URL)
    def refused(url): raise HTTPError(url, 403, "Forbidden", {}, None)
    monkeypatch.setattr(fetch, "get", refused)
    with pytest.raises(SystemExit, match=f"^{URL}: HTTP 403$"):
        fetch.page(URL)


def test_a_fetched_reference_is_kept():
    Path("output/data/scryfall-syntax.md").write_text("## Scryfall Search Reference\n")
    out = run("scryfall/fetch-syntax.py")
    assert (out.returncode, out.stdout) == (0, "output/data/scryfall-syntax.md (already fetched)\n")


def answer(name):
    return load("scryfall/search.py").answer((SAVED / name).read_bytes())


def test_a_search_prints_its_count_warnings_and_first_20_cards():
    lines = answer("search.json").splitlines()
    assert lines[:2] == ["44 cards, the first 20:", "Warning: Invalid expression “foo:bar” was ignored. Unknown keyword “foo”."]
    assert len(lines) == 22
    assert lines[4] == "Birgi, God of Storytelling // Harnfel, Horn of Bounty | Legendary Creature — God // Legendary Artifact"
    assert lines[-1] == "Gruul Locket | Artifact"


def test_an_error_prints_scryfalls_details_and_warnings():
    assert answer("error.json") == ("All of your terms were ignored.\n"
                                    "Warning: Invalid expression “foo:bar” was ignored. Unknown keyword “foo”.")
