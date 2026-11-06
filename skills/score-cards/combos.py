"""A deck's combo facts from Commander Spellbook, its <run_dir>/<slug>-combos.md, for facts.py.
write() matches output/decks/<slug>/list.txt, commanders included, against Spellbook's bulk variants file, cut at
download to the fields read here and cached in output/data/variants.json.gz, fetched again when missing or a day old,
and posts the list to estimate-bracket; writes the Included table (each combo whose cards are all in the list, within
the commanders' colour identity, its result, whether Spellbook marks it a definite or arguable two-card combo), the
Almost included table (combos one card short whose missing card is in the deck's Adds tables), each with the combo's
bracket tag and salt, and the cards Spellbook flags as mass land denial or extra turns. Prints the deck's names
Spellbook does not know. If Spellbook does not answer, or sends a variants file without variants, a cached variants file
is used however old and the title line says so; with none, or with no JSON holding cards and combos from
estimate-bracket, prints one line naming the URL and writes nothing."""
import gzip, json, sys, time
from functools import cache
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from net import get, Failed
from project import key, decklist, write as save, DECKS, DATA, ORACLE
from tables import table, adds

SPELLBOOK = "https://backend.commanderspellbook.com"
BULK = "https://json.commanderspellbook.com/variants.json.gz"
VARIANTS = DATA / "variants.json.gz"
DAY = 24 * 60 * 60
FLAGS = {"massLandDenial": "mass land denial", "extraTurn": "extra turns"}
TAGS = {"R": "Ruthless", "S": "Spicy", "P": "Powerful", "O": "Oddball", "C": "Core", "E": "Exhibition", "B": "Banned"}

def ask(endpoint, body):
    """Spellbook's JSON answer to body at endpoint, or None after printing the URL when there is none or it lacks
    cards and combos"""
    url = f"{SPELLBOOK}/{endpoint}/"
    try:
        if {"cards", "combos"} <= set(answer := json.loads(get(url, body))): return answer
    except (OSError, ValueError, TypeError, Failed): pass
    print(f"Commander Spellbook unreachable: {url}")

def combo(v):
    """(id, card names, result, identity, bracket tag, salt) of a variant"""
    salt = "-" if v["salt"] is None else f"{v['salt']:.1f}"
    return (v["id"], [u["card"]["name"] for u in v["uses"]], ", ".join(p["feature"]["name"] for p in v["produces"]),
            set(v["identity"]) - {"C"}, TAGS.get(v["bracketTag"], v["bracketTag"]), salt)

def parse(data):
    """the combos of the variants file's bytes, the most played first"""
    return [combo(v) for v in sorted(json.loads(gzip.decompress(data))["variants"], key=lambda v: -(v["popularity"] or 0))]

def slim(data):
    """the variants file's bytes with each variant cut to the fields combo() and parse() read"""
    keep = lambda v: {"id": v["id"], "uses": [{"card": {"name": u["card"]["name"]}} for u in v["uses"]],
                      "produces": [{"feature": {"name": p["feature"]["name"]}} for p in v["produces"]],
                      **{f: v[f] for f in ("identity", "bracketTag", "salt", "popularity")}}
    variants = [keep(v) for v in json.loads(gzip.decompress(data))["variants"]]
    return gzip.compress(json.dumps({"variants": variants}, separators=(",", ":")).encode())

@cache
def variants():
    """(every combo, the date of the stale copy they come from or None), the cached file fetched again when missing or
    a day old; None when Spellbook does not send it, or sends a file without variants, and nothing is cached"""
    if VARIANTS.exists() and time.time() - VARIANTS.stat().st_mtime < DAY: return parse(VARIANTS.read_bytes()), None
    try:
        save(VARIANTS, data := slim(get(BULK)))
        return parse(data), None
    except (OSError, ValueError, EOFError, KeyError, TypeError, Failed):
        if not VARIANTS.exists(): return None
        return parse(VARIANTS.read_bytes()), time.strftime("%Y-%m-%d", time.localtime(VARIANTS.stat().st_mtime))

def identity(commanders):
    """the colours of the commanders' colour identity in oracle.json"""
    fronts = {key(n).lower(): e for n, e in json.loads(ORACLE.read_text())["cards"].items()}
    return {c for _, n in commanders for c in fronts.get(key(n).lower(), {}).get("color_identity", [])}

def two_card(c):
    return "definite" if c.get("definitelyTwoCard") else "arguable" if c.get("arguablyTwoCard") else "no"

def page(slug, combos, stale, deck, colours, bracket, adds):
    """the combos file's text from the combos, the keys of the deck's cards, its colours, Spellbook's bracket answer and
    the keys of the deck's Adds"""
    marks = {c["combo"]["id"]: two_card(c) for c in bracket["combos"]}
    included, almost = [], []
    for vid, names, result, colour, tag, salt in combos:
        if not colour <= colours: continue
        missing = [n for n in names if key(n).lower() not in deck]
        if not missing: included.append([" + ".join(names), result, marks.get(vid, "-"), tag, salt])
        elif len(missing) == 1 and key(missing[0]).lower() in adds:
            row = [missing[0], " + ".join(n for n in names if n not in missing), result, tag, salt]
            if row not in almost: almost.append(row)
    flagged = [[c["card"]["name"], FLAGS[f]] for c in bracket["cards"] for f in FLAGS if c.get(f)]
    source = "commanderspellbook.com" + (f", from a stale copy of {stale}" if stale else "")
    return "\n".join([f"# {slug}: combos from {source}", "",
                      "## Included", table("| Cards | Result | Two-card | Bracket tag | Salt |", included), "",
                      "## Almost included", table("| Missing | Present | Result | Bracket tag | Salt |", almost), "",
                      "## Flagged cards", table("| Card | Flag |", flagged), ""])

def write(run, slug):
    commanders, rest = decklist(slug)
    body = {"commanders": [{"card": n} for _, n in commanders], "main": [{"card": n, "quantity": c} for c, n in rest]}
    if (found := variants()) is None:
        print(f"Commander Spellbook unreachable: {BULK}")
        return
    if (bracket := ask("estimate-bracket", body)) is None: return
    known = {key(c["card"]["name"]).lower() for c in bracket["cards"]}
    if unknown := [n for _, n in commanders + rest if key(n).lower() not in known]:
        print(f"{slug}: not on Commander Spellbook:", ", ".join(unknown))
    deck = {key(n).lower() for _, n in commanders + rest}
    candidates = {key(r[0]).lower() for r in adds(DECKS / slug)}
    Path(run, f"{slug}-combos.md").write_text(page(slug, *found, deck, identity(commanders), bracket, candidates))
