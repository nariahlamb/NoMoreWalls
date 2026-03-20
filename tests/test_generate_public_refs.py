from __future__ import annotations

import json
from pathlib import Path

from generate_public_refs import build_public_source_links, fetch_gist, load_manifest, resolve_gist_inputs


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


def test_resolve_gist_inputs_prefers_local_metadata(tmp_path: Path, monkeypatch) -> None:
    metadata_path = tmp_path / "gist-sync-metadata.json"
    metadata_path.write_text(
        json.dumps(
            {
                "gist_id": "keep-gist",
                "gist_url": "https://gist.github.com/owner/keep-gist",
                "updated_at": "2026-03-20T00:00:00Z",
                "source_links": {
                    "list.txt": "https://example.test/list.txt",
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "generate_public_refs.fetch_gist",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("不应调用 Gist API")),
    )

    gist, source_links = resolve_gist_inputs("keep-gist", token="token", local_metadata_file=Path(metadata_path))

    assert gist["id"] == "keep-gist"
    assert source_links["list.txt"] == "https://example.test/list.txt"


def test_build_public_source_links_filters_private_entries() -> None:
    public_links = build_public_source_links(
        {
            "list.txt": "https://example.test/list.txt",
            "snippets/nodes.yml": "https://example.test/nodes.yml",
            "snippets/_config.yml": "https://example.test/_config.yml",
            "list_raw.txt": "https://example.test/list_raw.txt",
            "artifacts/quality/summary.md": "https://example.test/summary.md",
        }
    )

    assert sorted(public_links) == ["list.txt", "snippets/nodes.yml"]
