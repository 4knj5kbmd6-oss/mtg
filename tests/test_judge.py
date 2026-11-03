import pytest
from conftest import run
import fetch_rules


def rule(*args):
    return run("skills/judge/rule.py", *args)


def test_a_number_prints_its_subrules():
    out = rule("100.1")
    assert out.returncode == 0
    assert out.stdout.splitlines()[:3] == ["100.1. These rules apply to any game with two or more players.",
                                           "100.1a A two-player game begins with only two players.",
                                           "100.1b A multiplayer game begins with more than two players."]


def test_a_section_prints_every_rule_under_it():
    numbers = [l.split()[0] for l in rule("800").stdout.splitlines() if l[:1].isdigit()]
    assert numbers == ["800.", "800.4.", "800.4a"]


def test_a_lettered_rule_stands_alone_with_its_example():
    out = rule("800.4a")
    assert out.stdout == ("800.4a When a player leaves the game, all objects that player owns leave the game.\n"
                          "Example: Alex leaves the game, and the Aura Alex controls leaves with Alex.\n\n")


def test_find():
    assert rule("--find", "player", "LEAVES").stdout == (
        "800.4a  When a player leaves the game, all objects that player owns leave the game.\n")


def test_glossary():
    out = rule("--glossary", "Abandon")
    assert out.returncode == 0
    assert out.stdout.startswith("Abandon\nTo turn a face-up ongoing scheme card face down.")


def test_a_miss_exits_1():
    assert (rule("999.9").returncode, rule("--glossary", "Nothing").returncode) == (1, 1)
    assert rule("100.1", "999.9").stdout.endswith("no rule 999.9\n\n")


def card(name):
    return run("skills/judge/card.py", name).stdout


def test_a_card_name_beats_another_cards_face():
    assert card("Tidal Insight") == "Tidal Insight {2}{U}\nInstant\nDraw two cards.\nRulings: none\n"
    assert card("Drowned Scholar").startswith("Drowned Scholar {1}{U}\n")
    assert card("Tidal Flats").startswith("Rising Tide {1}{U}\n")


def test_a_rules_page_with_no_link_exits_naming_it(monkeypatch):
    monkeypatch.setattr(fetch_rules, "get", lambda url: b"<html>moved</html>")
    with pytest.raises(SystemExit, match="^https://magic.wizards.com/en/rules: no link to the Comprehensive Rules .txt$"):
        fetch_rules.main()
