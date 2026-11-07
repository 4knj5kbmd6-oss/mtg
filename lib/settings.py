"""The owner's settings.json, read from the folder that holds output/, over the DEFAULTS below (keys described in
README.md); a partial models, quota or cart merges over its default key by key.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/lib/settings.py [key=value ...]
prints the effective settings as JSON, each key=value overriding that setting for this run (a dotted key reaches a
nested one, quota.adds=15; a value is JSON when it parses, a string otherwise); settings.json is not written.
A settings.json that is not a JSON object, or a top-level value of the wrong kind in it or in a key=value word, stops
the run with one line naming the file or the word; a top-level key not in DEFAULTS is named on stderr, the run going
on."""
import json, sys
from pathlib import Path
DEFAULTS = {"scorers": 3, "rankers": 4, "exclude_priciest": 3,
            "models": {"scorer": "claude-sonnet-5-5", "ranker": "claude-sonnet-5-5", "researcher": "claude-opus-5-5",
                       "judge": "claude-sonnet-5-5", "librarian": "claude-sonnet-5-5", "shopper": "claude-sonnet-5-5",
                       "planner": "claude-opus-5-5"},
            "budget": None,
            "quota": {"adds": 20, "lands": 5, "cuts": [10, 15]}, "universes_beyond": True, "new_sets": False, "images": True,
            "cart": {"condition": "MP", "language": "English", "finish": None, "premium": None}}
WHOLE, FLAG = ("a whole number ≥ 1", lambda v: type(v) is int and v >= 1), ("true or false", lambda v: type(v) is bool)
KIND = {"scorers": WHOLE, "rankers": WHOLE, "exclude_priciest": ("a whole number ≥ 0", lambda v: type(v) is int and v >= 0),
        "universes_beyond": FLAG, "new_sets": FLAG, "images": FLAG,
        "budget": ("a number or null", lambda v: v is None or type(v) in (int, float)),
        **{k: ("an object", lambda v: isinstance(v, dict)) for k, v in DEFAULTS.items() if isinstance(v, dict)}}

def check(source, key, value):
    """stop the run, naming source, when key's value is not of its kind"""
    if key in KIND and not KIND[key][1](value): sys.exit(f"{source}: {key} must be {KIND[key][0]}")

def settings(overrides=()):
    """the effective settings, with each key=value word of overrides applied"""
    p = Path("settings.json")
    try: given = json.loads(p.read_text()) if p.exists() else {}
    except ValueError as e: sys.exit(f"settings.json: {e}")
    if not isinstance(given, dict): sys.exit("settings.json: not an object")
    for k, v in given.items():
        if k not in DEFAULTS: print(f"settings.json: unknown key {k}", file=sys.stderr)
        check("settings.json", k, v)
    nested = {k: {**v, **given.get(k, {})} for k, v in DEFAULTS.items() if isinstance(v, dict)}
    out = {**DEFAULTS, **given, **nested}
    for word in overrides:
        path, _, raw = word.partition("=")
        *outer, last = path.split(".")
        d = out
        for k in outer: d = d.setdefault(k, {})
        try: d[last] = json.loads(raw)
        except ValueError: d[last] = raw
        check(word, top := path.split(".")[0], out[top])
    return out

if __name__ == "__main__":
    if not all("=" in w for w in sys.argv[1:]): sys.exit(__doc__)
    print(json.dumps(settings(sys.argv[1:])))
