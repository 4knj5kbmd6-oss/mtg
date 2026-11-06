import http.client, io, re, socket, urllib.error
import pytest
import net

URL = "https://api.scryfall.com/cards/named?exact=Sol%20Ring"


def answers(monkeypatch, *given):
    """urlopen answering each request in turn: an int is that HTTP error, an exception is raised, bytes are the body;
    returns the (request, timeout) of each call. Waits take no time."""
    calls = []
    def urlopen(req, timeout):
        calls.append((req, timeout))
        a = given[len(calls) - 1]
        if isinstance(a, int): raise urllib.error.HTTPError(req.full_url, a, "", {}, None)
        if isinstance(a, Exception): raise a
        return io.BytesIO(a)
    monkeypatch.setattr(net.urllib.request, "urlopen", urlopen)
    monkeypatch.setattr(net.time, "sleep", lambda s: None)
    return calls


@pytest.mark.parametrize("status", [429, 503])
def test_a_429_or_5xx_is_retried_once(monkeypatch, status):
    calls = answers(monkeypatch, status, b"{}")
    assert net.get(URL) == b"{}"
    assert [t for _, t in calls] == [net.TIMEOUT, net.TIMEOUT]


def test_a_second_429_or_5xx_exits_naming_the_url_and_status(monkeypatch):
    answers(monkeypatch, 429, 503)
    with pytest.raises(net.Failed, match=f"^{re.escape(URL)}: HTTP 503$"):
        net.get(URL)


@pytest.mark.parametrize("error", [urllib.error.URLError(socket.timeout("timed out")), socket.timeout("timed out")])
def test_a_timeout_exits_naming_the_url(monkeypatch, error):
    calls = answers(monkeypatch, error)
    with pytest.raises(SystemExit, match=f"^{re.escape(URL)}: timed out$"):
        net.get(URL)
    assert len(calls) == 1


def test_another_http_error_is_raised_as_it_came(monkeypatch):
    calls = answers(monkeypatch, 404, 404)
    with pytest.raises(urllib.error.HTTPError):
        net.get(URL)
    assert net.found(URL) is None
    assert len(calls) == 2


def test_requests_are_paced_and_carry_the_tools_headers(monkeypatch):
    calls = answers(monkeypatch, b"{}", b"{}")
    waits = []
    monkeypatch.setattr(net.time, "sleep", waits.append)
    monkeypatch.setattr(net, "last", 0.0)
    net.get(URL)
    net.get("https://backend.commanderspellbook.com/estimate-bracket/", {"commanders": []})
    assert waits[0] == 0 and 0.09 < waits[1] <= 0.1
    (get, _), (post, _) = calls
    assert (get.get_method(), get.data) == ("GET", None)
    assert get.headers == {"User-agent": "mtg-toolbox", "Accept": "application/json;q=0.9,*/*;q=0.8"}
    assert (post.get_method(), post.data) == ("POST", b'{"commanders": []}')
    assert post.headers == {**get.headers, "Content-type": "application/json"}


def test_no_test_reaches_the_network():
    with pytest.raises(net.Failed, match="^https://api.scryfall.com/bulk-data: "):
        net.get("https://api.scryfall.com/bulk-data")


def test_a_truncated_answer_exits_naming_the_url(monkeypatch):
    class Truncated(io.BytesIO):
        def read(self, *a): raise http.client.IncompleteRead(b"par", 10)
    monkeypatch.setattr(net.urllib.request, "urlopen", lambda req, timeout: Truncated())
    with pytest.raises(net.Failed, match=f"^{re.escape(URL)}: IncompleteRead\\(3 bytes read, 10 more expected\\)$"):
        net.get(URL)
