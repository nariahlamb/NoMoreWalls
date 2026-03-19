from __future__ import annotations

from generate_public_refs import fetch_gist, load_manifest


class FakeResponse:
    def __init__(self, status_code: int, payload=None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_fetch_gist_retries_retryable_errors(monkeypatch) -> None:
    responses = iter(
        [
            FakeResponse(500, text="server error"),
            FakeResponse(200, payload={"id": "keep-gist"}),
        ]
    )

    def fake_get(_url: str, headers, timeout: int):
        assert headers["User-Agent"] == "NoMoreWalls-public-refs"
        assert timeout == 30
        return next(responses)

    monkeypatch.setattr("generate_public_refs.requests.get", fake_get)
    monkeypatch.setattr("generate_public_refs.time.sleep", lambda _seconds: None)

    gist = fetch_gist("keep-gist", token="token")

    assert gist["id"] == "keep-gist"


def test_load_manifest_retries_retryable_errors(monkeypatch) -> None:
    responses = iter(
        [
            FakeResponse(502, text="bad gateway"),
            FakeResponse(200, payload={"files": [{"source": "list.txt", "gist": "list.txt"}]}),
        ]
    )

    def fake_get(_url: str, headers, timeout: int):
        assert headers["User-Agent"] == "NoMoreWalls-public-refs"
        assert timeout == 30
        return next(responses)

    monkeypatch.setattr("generate_public_refs.requests.get", fake_get)
    monkeypatch.setattr("generate_public_refs.time.sleep", lambda _seconds: None)

    manifest = load_manifest(
        gist={"files": {"manifest.json": {"raw_url": "https://example.test/manifest.json"}}},
        token="token",
    )

    assert manifest["files"][0]["source"] == "list.txt"
