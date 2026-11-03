"""Write a deck's combo facts from Commander Spellbook to <run_dir>/<slug>-combos.md.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/combos.py <run_dir> <slug>
posts output/decks/<slug>/list.txt, commanders first, to Spellbook's find-my-combos and estimate-bracket; writes the
Included table (each combo's cards, its result, whether Spellbook marks it a definite or arguable two-card combo),
the Almost included table (combos one card away whose missing card is in the deck's Adds tables) and the cards
Spellbook flags as mass land denial or extra turns. Prints the deck's names Spellbook does not know. If Spellbook is
unreachable or answers with no JSON, prints one line naming the URL and writes nothing."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from merge import get, key, table, decklist, adds, DECKS

SPELLBOOK = "https://backend.commanderspellbook.com"
FLAGS = {"massLandDenial": "mass land denial", "extraTurn": "extra turns"}

def ask(endpoint, body):
    """Spellbook's JSON answer to body at endpoint, or None after printing the URL when there is none"""
    url = f"{SPELLBOOK}/{endpoint}/"
    try: return json.loads(get(url, body))
    except (OSError, ValueError): print(f"Commander Spellbook unreachable: {url}")

def names(variant): return [u["card"]["name"] for u in variant["uses"]]

def result(variant): return ", ".join(p["feature"]["name"] for p in variant["produces"])

def two_card(c):
    return "definite" if c.get("definitelyTwoCard") else "arguable" if c.get("arguablyTwoCard") else "no"

def page(slug, combos, bracket, adds):
    """the combos file's text from the two Spellbook answers and the keys of the deck's Adds"""
    marks = {c["combo"]["id"]: two_card(c) for c in bracket["combos"]}
    included = [[" + ".join(names(v)), result(v), marks.get(v["id"], "-")] for v in combos["included"]]
    deck = {key(c["card"]["name"]).lower() for c in bracket["cards"]}
    almost = []
    for v in combos["almostIncluded"]:
        missing = [n for n in names(v) if key(n).lower() not in deck]
        if not missing or any(key(n).lower() not in adds for n in missing): continue
        row = [", ".join(missing), " + ".join(n for n in names(v) if n not in missing), result(v)]
        if row not in almost: almost.append(row)
    flagged = [[c["card"]["name"], FLAGS[f]] for c in bracket["cards"] for f in FLAGS if c.get(f)]
    return "\n".join([f"# {slug}: Commander Spellbook combos", "",
                      "## Included", table("| Cards | Result | Two-card |", included), "",
                      "## Almost included", table("| Missing | Present | Result |", almost), "",
                      "## Flagged cards", table("| Card | Flag |", flagged), ""])

def main():
    if len(sys.argv) != 3: sys.exit(__doc__)
    run, slug = sys.argv[1], sys.argv[2]
    commanders, rest = decklist(slug)
    body = {"commanders": [{"card": n} for _, n in commanders], "main": [{"card": n, "quantity": c} for c, n in rest]}
    if (combos := ask("find-my-combos", body)) is None or (bracket := ask("estimate-bracket", body)) is None: return
    known = {key(c["card"]["name"]).lower() for c in bracket["cards"]}
    if unknown := [n for _, n in commanders + rest if key(n).lower() not in known]:
        print("not on Commander Spellbook:", ", ".join(unknown))
    candidates = {key(r[0]).lower() for r in adds(DECKS / slug)}
    Path(run, f"{slug}-combos.md").write_text(page(slug, combos["results"], bracket, candidates))

if __name__ == "__main__": main()
