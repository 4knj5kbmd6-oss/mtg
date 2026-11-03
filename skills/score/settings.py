"""The owner's settings.json, read from the folder that holds output/, with the DEFAULTS below for absent keys:
scorers (independent scorers per deck), model (the model every dispatched agent runs on), budget
(the highest TCGplayer market price in dollars an add may carry; None for no cap), quota (the researcher lists
exactly `adds` nonland adds, up to `lands` land adds, and between cuts[0] and cuts[1] cuts), universes_beyond
(False leaves Universes Beyond sets out of research) and cart (the worst condition allowed, as NM, LP, MP or HP;
the language; the finish, nonfoil, foil or either; the premium in dollars the buyer pays to remove one package,
0 for the lowest price, a large number for the fewest packages). A cart value of None is asked each cart; a value
set is not asked. A partial quota or cart merges over its default key by key.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/settings.py
prints the effective settings as JSON."""
import json
from pathlib import Path
DEFAULTS = {"scorers": 3, "model": "claude-opus-5-5", "budget": None,
            "quota": {"adds": 20, "lands": 5, "cuts": [10, 15]}, "universes_beyond": True,
            "cart": {"condition": "MP", "language": "English", "finish": None, "premium": None}}

def settings():
    p = Path("settings.json")
    given = json.loads(p.read_text()) if p.exists() else {}
    nested = {k: {**v, **given.get(k, {})} for k, v in DEFAULTS.items() if isinstance(v, dict)}
    return {**DEFAULTS, **given, **nested}

if __name__ == "__main__": print(json.dumps(settings()))
