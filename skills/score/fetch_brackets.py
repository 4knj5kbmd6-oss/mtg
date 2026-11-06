"""Fetch Wizards' Commander Brackets announcement and its updates into output/data/brackets.md, one ## section per
article of PAGES, in their date order.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/score/fetch_brackets.py
Fetches only the articles the file lacks, matched by their Source lines, so an article added to PAGES is fetched alone.
Each section is the article's heading, its URL and its text up to the article's end, read by fetch_syntax's parser. A
page that answers other than 200, or with Cloudflare's challenge, stops the run with one line naming its URL. Prints
each section's heading and size."""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scryfall"))
from fetch_syntax import section, page
from project import write, DATA

NEWS = "https://magic.wizards.com/en/news/announcements/"
PAGES = [NEWS + p for p in ("introducing-commander-brackets-beta",  # Feb 11, 2025
                            "commander-brackets-beta-update-april-22-2025",
                            "commander-brackets-beta-update-october-21-2025",
                            "commander-brackets-beta-update-february-9-2026")]
BRACKETS = DATA / "brackets.md"

def sections(text):
    """{url: section} of the file's text, by each section's Source line"""
    return {m.group(1): s.rstrip("\n") + "\n" for s in re.split(r"(?m)^(?=## )", text)
            if (m := re.search(r"^Source: (\S+)$", s, re.M))}

def main():
    have = sections(BRACKETS.read_text()) if BRACKETS.exists() else {}
    have |= {u: section(page(u).split("</article>")[0], u) for u in PAGES if u not in have}
    write(BRACKETS, "\n".join(have[u] for u in PAGES))
    for u in PAGES: print(f"{have[u].splitlines()[0]}  ({len(have[u]):,} characters)")

if __name__ == "__main__": main()
