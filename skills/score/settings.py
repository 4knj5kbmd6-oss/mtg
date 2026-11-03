"""The owner's settings.json, read from the folder that holds output/, with the DEFAULTS below for absent keys:
scorers (independent scorers per deck), model (the model every dispatched agent runs on), budget
(the highest TCGplayer market price in dollars an add may carry; None for no cap), quota (the researcher lists
exactly `adds` nonland adds, up to `lands` land adds, and between cuts[0] and cuts[1] cuts), universes_beyond
(False leaves Universes Beyond sets out of research) and cart (the worst condition allowed, as NM, LP, MP or HP;
the language; the finish, nonfoil, foil or either; the premium in dollars the buyer pays to remove one package,
0 for the lowest price, a large number for the fewest packages). A cart value of None is asked each cart; a value
set is not asked. A partial quota or cart merges over its default key by key.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/settings.py [key=value ...]
prints the effective settings as JSON, each key=value overriding that setting for this run (a dotted key reaches a
nested one, quota.adds=15; a value is JSON when it parses, a string otherwise); settings.json is not written."""
import json, sys
from pathlib import Path
DEFAULTS = {"scorers": 3, "model": "claude-opus-5-5", "budget": None,
            "quota": {"adds": 20, "lands": 5, "cuts": [10, 15]}, "universes_beyond": True,
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
