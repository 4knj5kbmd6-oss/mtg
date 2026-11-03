"""Fetch Scryfall's search reference into output/data/scryfall-syntax.md, one ## section per docs page.
usage (from the folder that holds output/): python3 ${CLAUDE_PLUGIN_ROOT}/skills/scryfall/fetch_syntax.py [--refresh]
Downloads only when the file is missing or --refresh is given. Each section is a page's heading, its URL and its
text, code spans kept in backticks and every example search shown as its query, less the paragraph labelled
"Instructions for AI Agents" (a honeypot Scryfall plants for crawlers). A page that answers other than 200,
or with Cloudflare's challenge, stops the run with one line naming its URL. Prints each section's heading and size."""
import re, sys, urllib.parse
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
from net import get, CHALLENGE
from project import DATA

DOCS = "https://scryfall.com/docs/"
PAGES = [DOCS + p for p in ("syntax", "regular-expressions", "api", "api/cards/search", "api/cards/named",
                            "api/cards/autocomplete")]
SYNTAX = DATA / "scryfall-syntax.md"
SKIP = {"script", "style", "svg"}
BLOCKS = {"p", "div", "ul", "ol", "li", "table", "br", "blockquote", "dl", "dt", "dd"}
HONEYPOT = "Instructions for AI Agents"

class Text(HTMLParser):
    """a docs page's text from its <h1> to its footer: the h1 a ## heading over the page's URL, lower headings one
    level down, list items and example searches as "- " lines, table rows as "| cell | cell |" lines"""
    def __init__(self, url):
        super().__init__()
        self.url, self.out = url, []
        self.on = self.done = False
        self.skip = 0
        self.cell = self.row = False
        self.query, self.mark = None, 0   # an example search's query, and where its link's text starts in out

    def emit(self, s):
        if self.on and not self.done and not self.skip: self.out.append(s)

    def block(self, s):
        """a line break, or a space inside a table cell"""
        self.emit(" " if self.cell else s)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in SKIP: self.skip += 1
        elif tag == "footer": self.done = True
        elif tag == "h1": self.on = True; self.emit("## ")
        elif re.fullmatch(r"h[2-6]", tag): self.emit("\n\n" + "#" * (int(tag[1]) + 1) + " ")
        elif tag in ("td", "th"):
            if not self.row: self.emit("\n"); self.row = True
            self.emit("| "); self.cell = True
        elif tag == "li": self.block("\n- ")
        elif tag in BLOCKS: self.block("\n")
        elif tag == "code": self.emit("`")
        elif tag == "a" and a.get("href", "").startswith("/search?"):
            if "reference-example" in a.get("class", ""): self.emit("\n- ")
            self.query = urllib.parse.parse_qs(urllib.parse.urlparse(a["href"]).query).get("q", [""])[0]
            self.mark = len(self.out)

    def handle_endtag(self, tag):
        if tag in SKIP: self.skip -= 1
        elif tag == "h1": self.emit(f"\n\nSource: {self.url}\n\n")
        elif re.fullmatch(r"h[2-6]|p|ul|ol|table", tag): self.block("\n\n")
        elif tag in ("td", "th"): self.emit(" "); self.cell = False
        elif tag in ("tr", "thead") and self.row: self.emit("|"); self.row = False
        elif tag == "code": self.emit("`")
        elif tag == "a" and self.query is not None:
            if f"`{self.query}`" not in "".join(self.out[self.mark:]): self.emit(f": `{self.query}`")
            self.query = None

    def handle_data(self, data):
        self.emit(re.sub(r"\s+", " ", data))

def section(html, url):
    """the page's section: its heading, Source line and text, one blank line between blocks, the honeypot left out"""
    parser = Text(url)
    parser.feed(html)
    lines = [re.sub(r" +", " ", l).strip() for l in "".join(parser.out).split("\n")]
    blocks = re.split(r"\n{2,}", "\n".join(l for l in lines if l != "-").strip())
    return "\n\n".join(b for b in blocks if not b.startswith(HONEYPOT)) + "\n"

def page(url):
    """the page's HTML; a non-200 answer or Cloudflare's challenge exits naming the URL"""
    try: html = get(url).decode("utf-8", "replace")
    except HTTPError as e: sys.exit(f"{url}: HTTP {e.code}")
    if CHALLENGE.search(html): sys.exit(f"{url}: Cloudflare challenge")
    return html

if __name__ == "__main__":
    if SYNTAX.exists() and "--refresh" not in sys.argv[1:]:
        print(f"{SYNTAX} (already fetched)")
    else:
        sections = [section(page(u), u) for u in PAGES]
        SYNTAX.parent.mkdir(parents=True, exist_ok=True)
        SYNTAX.write_text("\n".join(sections))
        for s in sections: print(f"{s.splitlines()[0]}  ({len(s):,} characters)")
