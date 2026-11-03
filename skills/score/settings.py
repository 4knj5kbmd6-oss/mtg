"""The owner's settings.json, read from the folder that holds output/, with the DEFAULTS below for absent keys:
scorers (independent scorers per deck), model (the model every dispatched agent runs on) and budget
(the highest TCGplayer market price in dollars an add may carry; None for no cap).
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/settings.py
prints the effective settings as JSON."""
import json
from pathlib import Path
DEFAULTS = {"scorers": 3, "model": "claude-opus-5-5", "budget": None}

def settings():
    p = Path("settings.json")
    return {**DEFAULTS, **(json.loads(p.read_text()) if p.exists() else {})}

if __name__ == "__main__": print(json.dumps(settings()))
