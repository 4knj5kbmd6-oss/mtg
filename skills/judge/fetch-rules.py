"""Fetch the current Comprehensive Rules into output/data/rules.txt and write their headings to output/data/rules-index.md.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/fetch-rules.py
The rules file is the .txt linked from Wizards' rules page. The index heads with the rules' effective date and the
file's link, so a later run downloads only when the page links a different, newer file. Prints the effective date."""
import re, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "score"))
from merge import get

PAGE = "https://magic.wizards.com/en/rules"
RULES, INDEX = Path("output/data/rules.txt"), Path("output/data/rules-index.md")
HEADING = re.compile(r"\d\. |\d{3}\. ")   # 1. Game Concepts, 100. General

def decode(raw):
    """the file's text, UTF-8 (with or without a BOM) or else Windows-1252, with \\n line ends"""
    try: text = raw.decode("utf-8-sig")
    except UnicodeDecodeError: text = raw.decode("cp1252")
    return text.replace("\r\n", "\n").replace("\r", "\n")

def effective(text):
    return re.search(r"These rules are effective as of ([^.\n]+)\.", text).group(1)

def index(text, link):
    """the effective date and link, then every section and subsection heading and the Glossary"""
    lines = [l.strip() for l in text.splitlines()]
    body = lines[lines.index("Credits") + 1:]   # past the table of contents
    heads = [l if l[1] == "." else "   " + l for l in body[:body.index("Glossary")] if HEADING.match(l)]
    return f"# Comprehensive Rules, effective {effective(text)}\n\nSource: {link}\n\n" + "\n".join(heads) + "\n\nGlossary\n"

if __name__ == "__main__":
    page = get(PAGE).decode("utf-8", "replace")
    link = urllib.parse.quote(re.search(r'href="([^"]*CompRules[^"]*\.txt)"', page).group(1), safe=":/%")
    if RULES.exists() and INDEX.exists() and f"Source: {link}\n" in INDEX.read_text():
        print("Comprehensive Rules effective", effective(RULES.read_text()), "(already current)")
    else:
        text = decode(get(link))
        RULES.write_text(text)
        INDEX.write_text(index(text, link))
        print("Comprehensive Rules effective", effective(text), "(fetched)")
