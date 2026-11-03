"""HTTP for the scripts: paced requests to Scryfall, Commander Spellbook and Wizards."""
import json, re, time, urllib.error, urllib.request
SCRYFALL, UA = "https://api.scryfall.com", "mtg-toolbox"
SEARCH = f"{SCRYFALL}/cards/search?q="
CHALLENGE = re.compile(r"cf[-_]chl|challenge-platform|Just a moment")
last = 0.0

def get(url, body=None):
    """the response body to a GET of url, or a POST of body as JSON, at least 100 ms after the previous request"""
    global last
    time.sleep(max(0, last + 0.1 - time.monotonic()))
    head = {"User-Agent": UA, "Accept": "application/json;q=0.9,*/*;q=0.8"} | ({"Content-Type": "application/json"} if body else {})
    try: return urllib.request.urlopen(urllib.request.Request(url, body and json.dumps(body).encode(), head)).read()
    finally: last = time.monotonic()

def found(url):
    """get(url) parsed as JSON, or None on a 404"""
    try: return json.loads(get(url))
    except urllib.error.HTTPError as e:
        if e.code != 404: raise
