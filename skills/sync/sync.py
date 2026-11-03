"""Add the user's public Commander decks not seen before to moxfield.json, write output/decks/<slug>/list.txt
for every deck there that came back as deck data and output/data/tokens.md once every deck did, drop the rows of
changes.md the dump shows landed, except those noted unowned, then run apply-changes.py so every list is the
intended deck again. A deck that came back as anything else (Cloudflare's challenge page, an error) is left as it was.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/sync.py mox.json
mox.json is the JSON string returned by fetch.js (quoted or raw): {"user", "listing", "decks"}."""
import json, os, re, sys, subprocess, unicodedata
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "score"))
from merge import cells, match, CHALLENGE

MOXFIELD, CHANGES = Path("moxfield.json"), Path("changes.md")
UNBLOCK = "open moxfield.com in the browser pane, pass the check and rerun /sync"

def blocked(v):
    """why a fetched entry is not Moxfield data, or None when it is"""
    if isinstance(v, list) or "mainboard" in v: return None
    body = str(v.get("body", ""))
    if CHALLENGE.search(body): return "Cloudflare challenge"
    return f"unexpected answer, HTTP {v.get('status', '?')}"

def wanted(d):
    """a listed deck the username pass may add: public and Commander"""
    return d.get("visibility") == "public" and str(d.get("format", "")).lower().startswith("commander")

def slugify(name, taken):
    """the shortest run of the name's leading words not in taken, joined by hyphens"""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower().replace("'", "")
    words = re.findall(r"[a-z0-9]+", plain)
    words = [w for w in words if w not in ("the", "a", "an", "of")] or words or ["deck"]
    for n in range(1, len(words) + 1):
        if (slug := "-".join(words[:n])) not in taken: return slug
    return next(f"{slug}-{i}" for i in range(2, 999) if f"{slug}-{i}" not in taken)

def enlist(mox, listing, taken):
    """add every wanted listed deck not yet seen to mox (moxfield.json's dict); returns {id: slug} added"""
    seen = set(mox.setdefault("seen", [])) | set(mox["decks"])
    added = {}
    for d in filter(wanted, listing):
        if d["publicId"] in seen: continue
        added[d["publicId"]] = mox["decks"][d["publicId"]] = slugify(d["name"], taken)
        taken.add(added[d["publicId"]]); seen.add(d["publicId"])
    mox["seen"] = sorted(seen)
    return added

def tokens(decks):
    """tokens.md from {slug: fetched deck}"""
    uniq = {}
    for slug, v in decks.items():
        for t in v["tokens"]:
            if not t["type"].startswith("Token"): continue
            key = (t["name"], "".join(sorted(t["colors"] or [])), t["pt"], t["type"], t["text"])
            uniq.setdefault(key, {**t, "decks": set()})["decks"].add(slug)
    rows = sorted(uniq.values(), key=lambda e: (e["type"], e["name"], e["pt"]))
    out = ["# Tokens", "", "| Token | P/T | Colors | Type | Decks |", "|---|---|---|---|---|"]
    out += [f"| {e['name']} | {e['pt']} | {''.join(sorted(e['colors'] or [])) or '-'} | {e['type']} | {', '.join(sorted(e['decks']))} |" for e in rows]
    return "\n".join(out) + "\n"

def drop_landed(dumped):
    """remove the rows of changes.md that the dumped lists show landed (In card in the deck or In blank, Out card gone
    or Out blank), except those noted unowned; print each. A card is matched by its front face, so a back face's name
    alone never matches."""
    if not CHANGES.exists(): return
    keep, landed = [], []
    for l in CHANGES.read_text().splitlines(keepends=True):
        c = next(iter(cells([l])), [])
        deck = dumped.get(c[0]) if len(c) >= 3 else None
        has = lambda name: any(map(match(name), deck))
        unowned = len(c) > 3 and "unowned" in c[3].lower()  # still to buy: stays until the owner clears the note
        if deck is not None and not unowned and (not c[1] or has(c[1])) and (not c[2] or not has(c[2])):
            landed.append(c)
        else: keep.append(l)
    if landed: CHANGES.write_text("".join(keep))
    for c in landed: print(f"landed: {c[0]} {c[1] or '-'} for {c[2] or '-'}", flush=True)

def main():
    if len(sys.argv) != 2: sys.exit(__doc__)
    raw = open(sys.argv[1]).read().strip()
    dump = json.loads(json.loads(raw) if raw.startswith('"') else raw)
    mox = json.loads(MOXFIELD.read_text()) if MOXFIELD.exists() else {"decks": {}}
    mox["user"] = dump["user"]
    if why := blocked(dump["listing"]):
        print(f"blocked: deck list of {dump['user']} ({why}); {UNBLOCK}")
    else:
        taken = set(mox["decks"].values()) | {p.name for p in Path("output/decks").glob("*") if p.is_dir()}
        for mid, slug in enlist(mox, dump["listing"], taken).items(): print(f"added: {slug} ({mid})")
    MOXFIELD.write_text(json.dumps({k: mox[k] for k in ("user", "decks", "seen") if k in mox}, indent=2, ensure_ascii=False) + "\n")

    fetched, dumped, stale = {}, {}, []
    for mid, slug in mox["decks"].items():
        v = dump["decks"].get(mid)
        if v is None or (why := blocked(v)):
            print(f"not in the dump: {slug}" if v is None else f"blocked: {slug} ({why}); {UNBLOCK}", flush=True)
            stale.append(slug); continue
        lines = v["commanders"] + [""] + v["mainboard"] + [""]
        if v["sideboard"]: lines += ["SIDEBOARD:"] + v["sideboard"] + [""]
        fetched[slug], dumped[slug] = v, lines
        os.makedirs(f"output/decks/{slug}", exist_ok=True)
        open(f"output/decks/{slug}/list.txt", "w").write("\n".join(lines))
    if not stale: open("output/data/tokens.md", "w").write(tokens(fetched))
    drop_landed(dumped)
    subprocess.run([sys.executable, str(Path(__file__).with_name("apply-changes.py"))], check=True)
    if stale: print(f"not refreshed: {', '.join(stale)} (tokens.md left as it was)")

if __name__ == "__main__": main()
