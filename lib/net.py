"""HTTP for the scripts: paced requests to Scryfall, Commander Spellbook, MTGJSON and Wizards."""
import http.client, json, re, time, urllib.error, urllib.request
SCRYFALL, UA = "https://api.scryfall.com", "mtg-toolbox"
MTGJSON = "https://mtgjson.com/api/v5"
SEARCH = f"{SCRYFALL}/cards/search?q="
CHALLENGE = re.compile(r"cf[-_]chl|challenge-platform|Just a moment")
TIMEOUT = 30  # seconds a server may stall before its request fails
last = 0.0

class Failed(SystemExit):
    """a request that failed for good; uncaught, it exits with one line naming the URL and why"""

def request(url, body):
    """the response body to a GET of url, or a POST of body as JSON, at least 100 ms after the previous request"""
    global last
    time.sleep(max(0, last + 0.1 - time.monotonic()))
    head = {"User-Agent": UA, "Accept": "application/json;q=0.9,*/*;q=0.8"} | ({"Content-Type": "application/json"} if body else {})
    req = urllib.request.Request(url, body and json.dumps(body).encode(), head)
    try: return urllib.request.urlopen(req, timeout=TIMEOUT).read()
    finally: last = time.monotonic()

def get(url, body=None):
    """request(url, body), a 429 or 5xx answer retried once a second later; another HTTP error is raised as it
    came, and a second 429 or 5xx, a timeout, no connection or a broken answer (a truncated body) raises Failed"""
    for again in (True, False):
        try: return request(url, body)
        except urllib.error.HTTPError as e:
            if e.code != 429 and e.code < 500: raise
            if not again: raise Failed(f"{url}: HTTP {e.code}")
            time.sleep(1)
        except (OSError, http.client.HTTPException) as e:
            raise Failed(f"{url}: {str(getattr(e, 'reason', e)) or type(e).__name__}")

def found(url):
    """get(url) parsed as JSON, or None on a 404"""
    try: return json.loads(get(url))
    except urllib.error.HTTPError as e:
        if e.code != 404: raise
