"""The skills, agents and README name only what exists."""
import re
from conftest import ROOT
import settings

DOCS = sorted((ROOT / "skills").glob("*/SKILL.md")) + sorted((ROOT / "agents").glob("*.md"))


def named(pattern):
    """(doc, match) for each match of pattern in the skills and agents"""
    return [(d.relative_to(ROOT), m) for d in DOCS for m in re.findall(pattern, d.read_text())]


def test_every_plugin_path_exists():
    paths = named(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]*[\w/])")
    assert paths and [(d, p) for d, p in paths if not (ROOT / p).exists()] == []


def test_every_named_agent_or_skill_exists():
    names = named(r"mtg-toolbox:([\w-]+)")
    exists = lambda n: (ROOT / "agents" / f"{n}.md").exists() or (ROOT / "skills" / n / "SKILL.md").exists()
    assert names and [(d, n) for d, n in names if not exists(n)] == []


def test_the_readmes_settings_are_the_defaults():
    section = (ROOT / "README.md").read_text().split("\n## Settings\n")[1].split("\n## ")[0]
    assert re.findall(r"^\| `(\w+)` \|", section, re.M) == list(settings.DEFAULTS)
