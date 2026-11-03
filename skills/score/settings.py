"""The owner's output/settings.json, read from the folder that holds output/, with defaults for absent keys:
scorers (independent scorers per deck), model (the model every dispatched agent runs on) and budget
(the highest TCGplayer market price in dollars an add may carry; None for no cap)."""
import json
from pathlib import Path
DEFAULTS = {"scorers": 3, "model": "claude-opus-5-5", "budget": None}

def settings():
    p = Path("output/settings.json")
    return {**DEFAULTS, **(json.loads(p.read_text()) if p.exists() else {})}
