import requests

from src.ftg.http_cache import CachedHttpClient


class FakeResponse:
    def __init__(self, text="ok", status_code=200):
        self.text = text
        self.status_code = status_code
        self.headers = {}

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"status {self.status_code}")
            error.response = self
            raise error


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def get(self, url, timeout):
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def test_fetch_writes_metadata_and_reuses_cache(tmp_path):
    session = FakeSession([FakeResponse("page")])
    sleeps = []
    client = CachedHttpClient(session, delay=0.25, sleep=sleeps.append)
    path = tmp_path / "page.html"

    first = client.fetch_text("https://example.test", path)
    second = client.fetch_text("https://example.test", path)

    assert first.text == second.text == "page"
    assert not first.from_cache
    assert second.from_cache
    assert session.calls == 1
    assert sleeps == [0.25]
    assert client.metadata_path(path).exists()


def test_fetch_retries_transient_request_errors(tmp_path):
    session = FakeSession([requests.ConnectionError("temporary"), FakeResponse("recovered")])
    sleeps = []
    client = CachedHttpClient(session, delay=0.5, retries=2, sleep=sleeps.append)
    result = client.fetch_text("https://example.test", tmp_path / "page.html")
    assert result.text == "recovered"
    assert session.calls == 2
    assert sleeps == [0.5, 0.5]
