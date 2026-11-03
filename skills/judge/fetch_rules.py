"""Fetch the current Comprehensive Rules into output/data/rules.txt.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/judge/fetch_rules.py
The rules file is the .txt linked from Wizards' rules page. Its first line is the file's link, so a later run
downloads only when the page links a different, newer file. Prints the effective date."""
import re, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from net import get
from project import write, RULES

PAGE = "https://magic.wizards.com/en/rules"

def decode(raw):
    """the file's text, UTF-8 (with or without a BOM) or else Windows-1252, with \\n line ends"""
    try: text = raw.decode("utf-8-sig")
    except UnicodeDecodeError: text = raw.decode("cp1252")
    return text.replace("\r\n", "\n").replace("\r", "\n")

def effective(text):
    return re.search(r"These rules are effective as of ([^.\n]+)\.", text).group(1)

def main():
    page = get(PAGE).decode("utf-8", "replace")
    if not (href := re.search(r'href="([^"]*CompRules[^"]*\.txt)"', page)):
        sys.exit(f"{PAGE}: no link to the Comprehensive Rules .txt")
    link = urllib.parse.quote(href.group(1), safe=":/%")
    if RULES.exists() and RULES.read_text().partition("\n")[0] == f"Source: {link}":
        print("Comprehensive Rules effective", effective(RULES.read_text()), "(already current)")
    else:
        text = decode(get(link))
        write(RULES, f"Source: {link}\n{text}")
        print("Comprehensive Rules effective", effective(text), "(fetched)")

if __name__ == "__main__": main()
