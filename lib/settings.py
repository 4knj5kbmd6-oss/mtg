"""The owner's settings.json, read from the folder that holds output/, over the DEFAULTS below (keys described in
README.md); a partial models, quota or cart merges over its default key by key.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/lib/settings.py [key=value ...]
prints the effective settings as JSON, each key=value overriding that setting for this run (a dotted key reaches a
nested one, quota.adds=15; a value is JSON when it parses, a string otherwise); settings.json is not written."""
import json, sys
from pathlib import Path
DEFAULTS = {"scorers": 3, "rankers": 3,
            "models": {"scorer": "claude-sonnet-5-5", "ranker": "claude-sonnet-5-5", "researcher": "claude-opus-5-5",
                       "judge": "claude-sonnet-5-5", "librarian": "claude-sonnet-5-5", "shopper": "claude-sonnet-5-5"},
            "budget": None,
            "quota": {"adds": 20, "lands": 5, "cuts": [10, 15]}, "universes_beyond": True, "new_sets": False, "images": True,
            "cart": {"condition": "MP", "language": "English", "finish": None, "premium": None}}

def settings(overrides=()):
    """the effective settings, with each key=value word of overrides applied"""
    p = Path("settings.json")
    given = json.loads(p.read_text()) if p.exists() else {}
    nested = {k: {**v, **given.get(k, {})} for k, v in DEFAULTS.items() if isinstance(v, dict)}
    out = {**DEFAULTS, **given, **nested}
    for word in overrides:
        path, _, raw = word.partition("=")
        *outer, last = path.split(".")
        d = out
        for k in outer: d = d.setdefault(k, {})
        try: d[last] = json.loads(raw)
        except ValueError: d[last] = raw
    return out

if __name__ == "__main__":
    if not all("=" in w for w in sys.argv[1:]): sys.exit(__doc__)
    print(json.dumps(settings(sys.argv[1:])))
