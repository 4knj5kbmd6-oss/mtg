"""Write output/decks/<slug>/list.txt and output/data/tokens.md from a Moxfield dump.
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
print(subprocess.run(["git", "diff", "--stat"], capture_output=True, text=True).stdout or "no changes")
