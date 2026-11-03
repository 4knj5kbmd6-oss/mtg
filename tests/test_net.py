import io, re, socket, urllib.error
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
