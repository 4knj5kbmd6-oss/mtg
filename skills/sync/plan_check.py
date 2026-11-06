"""Print each card name a deck's plan.md names that is not in its list.txt, one line each, "<slug>: <name> is not in
list.txt". The names are every card of its Win bullets' roles, joined by +, each role one card or a role name with its
cards in brackets separated by ;, and its Not cast cards, separated by ;. A list written with commas is read too: the
longest run of comma-separated parts that names a listed card is taken, a card name holding commas. A deck with no
plan.md prints nothing.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/plan_check.py <slug> [slug ...]
       python3 ${CLAUDE_PLUGIN_ROOT}/skills/sync/plan_check.py --plan <path> <slug>  checks the plan at path, a draft
       outside output/, against the slug's list.txt"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from project import DECKS, decklist

def field(label, text):
    """the text after each `- **<label>:**` bullet of text"""
    return re.findall(rf"^- \*\*{label}:\*\*[ \t]*(.*)$", text, re.M)

def names(text, known):
    """the card names of text, separated by ; or by commas, a comma-separated run taken whole when it names a known
    card (known: casefolded names)"""
    out = []
    for chunk in text.split(";"):
        parts = [p.strip() for p in chunk.split(", ")]
        while parts:
            j = next((j for j in range(len(parts), 0, -1) if ", ".join(parts[:j]).casefold() in known), 1)
            out.append(", ".join(parts[:j])); parts = parts[j:]
    return [n for n in out if n]

def win(text, known):
    """the cards of a Win bullet, `<name>: <role> + <role>. <sentence>`: a role in brackets gives the cards inside
    them, any other is one card; the last such, followed by the sentence, ends at the first full stop that leaves its
    name known, else at the first"""
    roles, out = re.split(r"\s+\+\s+", text.partition(": ")[2]), []
    for i, role in enumerate(roles):
        if group := re.match(r"[^(.]*\(([^)]*)\)", role):
            out += names(group[1], known); continue
        if i == len(roles) - 1:
            stops = [m.start() for m in re.finditer(r"\.(?=\s|$)", role)] + [len(role)]
            role = role[:next((s for s in stops if role[:s].casefold() in known), stops[0])]
        out += names(role, known)
    return out

def check(slug, plan=None):
    """the card names of plan, by default the deck's plan.md, not in the deck's list, in the plan's order"""
    plan = Path(plan) if plan else DECKS / slug / "plan.md"
    if not plan.exists(): return []
    commanders, rest = decklist(slug)
    known = {f.casefold() for _, n in commanders + rest for f in [n, *n.split(" // ")]}
    text = plan.read_text()
    cards = [n for w in field("Win", text) for n in win(w, known)]
    cards += [n for f in field("Not cast", text) for n in names(f, known)]
    return [n for n in dict.fromkeys(cards) if n.casefold() not in known]

def main():
    args, plan = sys.argv[1:], None
    if args[:1] == ["--plan"]:
        if len(args) != 3: sys.exit(__doc__)
        plan, args = args[1], args[2:]
    if not args: sys.exit(__doc__)
    for slug in args:
        for name in check(slug, plan): print(f"{slug}: {name} is not in list.txt")

if __name__ == "__main__": main()
