"""Write output/decks/<slug>/list.txt and output/data/tokens.md from a Moxfield dump,
then drop the rows of output/changes.md that have landed, except those noted unowned.
usage (repo root): python3 .claude/skills/mtg-sync/sync.py mox.json
mox.json is the JSON string returned by fetch.js (quoted or raw)."""
import json, os, sys, subprocess
if len(sys.argv) != 2: sys.exit(__doc__)
raw = open(sys.argv[1]).read().strip()
if raw.startswith('"'): raw = json.loads(raw)
d = json.loads(raw)
slugs = json.load(open("output/decks/moxfield.json"))["decks"]
uniq = {}
for mid, v in d.items():
    slug = slugs.get(mid)
    if not slug: print(f"skip {mid} ({v['name']}): not in output/decks/moxfield.json"); continue
    lines = v["commanders"] + [""] + v["mainboard"] + [""]
    if v["sideboard"]: lines += ["SIDEBOARD:"] + v["sideboard"] + [""]
    os.makedirs(f"output/decks/{slug}", exist_ok=True)
    open(f"output/decks/{slug}/list.txt", "w").write("\n".join(lines))
    for t in v["tokens"]:
        if not t["type"].startswith("Token"): continue
        key = (t["name"], "".join(sorted(t["colors"] or [])), t["pt"], t["type"], t["text"])
        uniq.setdefault(key, {**t, "decks": set()})["decks"].add(slug)
rows = sorted(uniq.values(), key=lambda e: (e["type"], e["name"], e["pt"]))
out = ["# Tokens", "", "Every token created by a card in the owned decks, from Moxfield's Tokens tab. Emblems and helper cards are left out.", "", "| Token | P/T | Colors | Type | Decks |", "|---|---|---|---|---|"]
out += [f"| {e['name']} | {e['pt']} | {''.join(sorted(e['colors'] or [])) or '-'} | {e['type']} | {', '.join(sorted(e['decks']))} |" for e in rows]
open("output/data/tokens.md", "w").write("\n".join(out) + "\n")

def cards(slug):
    """Every card name and face in a deck's list, lowercased; None if the deck has no list."""
    try: lines = open(f"output/decks/{slug}/list.txt").read().splitlines()
    except FileNotFoundError: return None
    names = set()
    for l in lines:
        qty, _, name = l.partition(" ")
        if qty.isdigit() and name.strip():
            name = name.strip().lower()
            names |= {name, *(f.strip() for f in name.split("//"))}
    return names

if os.path.exists("output/changes.md"):
    keep, landed = [], []
    for l in open("output/changes.md").read().splitlines(keepends=True):
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        deck = cards(c[0]) if l.startswith("|") and len(c) >= 3 and c[0] else None
        unowned = len(c) > 3 and "unowned" in c[3].lower()  # still to buy: stays until the owner clears the note
        if deck is not None and not unowned and (not c[1] or c[1].lower() in deck) and (not c[2] or c[2].lower() not in deck):
            landed.append(c)
        else: keep.append(l)
    if landed: open("output/changes.md", "w").write("".join(keep))
    for c in landed: print(f"landed: {c[0]} {c[1] or '-'} for {c[2] or '-'}")
print(subprocess.run(["git", "diff", "--stat"], capture_output=True, text=True).stdout or "no changes")
