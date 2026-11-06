"""Print each card name a deck's plan.md names that is not in its list.txt, one line each, "<slug>: <name> is not in
list.txt". The names are every card of its Win bullets' roles and its Not cast cards; its other lines name no card.
A Win bullet is `<name>: <role> + <role>. <sentence>`, with no name when no ": " comes before its first " + ". Its
roles end at the first full stop, followed by a space or the end and outside brackets, where the last role before it
is a bracket group or a known name, else at the first such stop. A role in brackets gives the cards inside them,
separated by ;, any other is one card; Not cast cards are separated by ;. A list written with commas is read too: the
longest run of comma-separated parts that names a known card is taken, a card name holding commas. The known names
are the list's and oracle.json's, both faces of each, the list's alone when there is no oracle.json. A deck with no
plan.md prints nothing; a --plan path that is not a file stops the run.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/plan_check.py <slug> [slug ...]
       python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/plan_check.py --plan <path> <slug>  checks the plan at path, a draft
       outside output/, against the slug's list.txt"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import DECKS, ORACLE, decklist, field, names, named
PLUS, GROUP = r"\s+\+\s+", r"[^()]*\(([^)]*)\)"

def win(text, known):
    """the cards of a Win bullet's roles (known: casefolded names)"""
    plus, colon = re.search(PLUS, text), text.find(": ")
    if 0 <= colon < (plus.start() if plus else len(text)): text = text[colon + 2:]
    depth, stops = 0, []
    for i, c in enumerate(text):
        depth += (c == "(") - (c == ")")
        if c == "." and not depth and (text[i + 1:i + 2] or " ").isspace(): stops.append(i)
    last = lambda s: re.split(PLUS, text[:s])[-1].strip()
    ends = [s for s in stops if re.fullmatch(GROUP, last(s)) or last(s).casefold() in known]
    out = []
    for role in re.split(PLUS, text[:(ends or stops or [len(text)])[0]]):
        group = re.fullmatch(GROUP, role.strip())
        out += names(group[1] if group else role, known)
    return out

def check(slug, plan=None):
    """the card names of plan, by default the deck's plan.md, not in the deck's list, in the plan's order"""
    if plan and not Path(plan).is_file(): sys.exit(f"no plan at {plan}")
    plan = Path(plan) if plan else DECKS / slug / "plan.md"
    if not plan.exists(): return []
    commanders, rest = decklist(slug)
    listed = {f.casefold() for _, n in commanders + rest for f in [n, *n.split(" // ")]}
    known = listed | (named().keys() if ORACLE.exists() else set())
    text = plan.read_text()
    cards = [n for w in field("Win", text) for n in win(w, known)]
    cards += [n for f in field("Not cast", text) for n in names(f, known)]
    return [n for n in dict.fromkeys(cards) if n.casefold() not in listed]

def main():
    args, plan = sys.argv[1:], None
    if args[:1] == ["--plan"]:
        if len(args) != 3: sys.exit(__doc__)
        plan, args = args[1], args[2:]
    if not args: sys.exit(__doc__)
    for slug in args:
        for name in check(slug, plan): print(f"{slug}: {name} is not in list.txt")

if __name__ == "__main__": main()
