"""Print Comprehensive Rules from output/data/rules.txt, which fetch-rules.py writes. Reads only; never fetches.
usage (from the folder that holds output/):
  python3 skills/judge/rule.py 800.4a [704.5 ...]      each rule with its subrules (800 prints every rule under 800)
  python3 skills/judge/rule.py --find word [word ...]  number and first 100 characters of each rule holding every word
  python3 skills/judge/rule.py --glossary term         the glossary entry for term"""
import re, sys
from pathlib import Path

RULES = Path("output/data/rules.txt")
NUMBER = re.compile(r"(\d(?:\d\d(?:\.\d+[a-z]*)?)?)\.? ")   # 8. section, 800. subsection, 800.4. rule, 800.4a and 704.5aa subrules

def parse(text):
    """the numbered rules as [number, text] in order, each rule's follow-on lines (its examples) folded in; the glossary as [entry]"""
    lines = [l.strip() for l in text.splitlines()]
    body = lines[lines.index("Credits") + 1:]   # past the table of contents
    glossary = body.index("Glossary")
    rules = []
    for l in body[:glossary]:
        if m := NUMBER.match(l): rules.append([m.group(1), l])
        elif l: rules[-1][1] += "\n" + l
    entries = "\n".join(body[glossary + 1:body.index("Credits")]).split("\n\n")
    return rules, [e.strip() for e in entries if e.strip()]

def under(n, q):
    """rule n is q or one of its subrules (a lettered subrule has none)"""
    return n == q or q[-1].isdigit() and n.startswith(q) and not n[len(q)].isdigit()

def main(args):
    if not args: sys.exit(__doc__)
    if not RULES.exists(): sys.exit(f"no {RULES}: run fetch-rules.py first")
    rules, glossary = parse(RULES.read_text())
    if args[0] == "--find":
        words = [w.casefold() for w in args[1:]]
        for n, t in rules:
            if all(w in t.casefold() for w in words): print(f"{n}  {t[len(n):].lstrip('. ').splitlines()[0][:100]}")
    elif args[0] == "--glossary":
        term = " ".join(args[1:]).casefold()
        heads = [e.splitlines()[0].casefold() for e in glossary]
        found = [e for e, h in zip(glossary, heads) if h == term] or [e for e, h in zip(glossary, heads) if term in h]
        print("\n\n".join(found) or f"no glossary entry for {term}")
        return not found
    else:
        missing = False
        for q in (a.rstrip(".") for a in args):
            found = [t for n, t in rules if under(n, q)]
            print("\n".join(found) or f"no rule {q}", end="\n\n")
            missing |= not found
        return missing

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
