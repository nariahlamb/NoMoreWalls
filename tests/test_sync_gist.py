from __future__ import annotations

from pathlib import Path

from sync_gist import build_authenticated_git_url, build_manifest, collect_sync_files, ensure_gist


class FakeGitHubClient:
    def __init__(self, gist=None, variable_value=None, viewer_login="owner") -> None:
        self.gist = gist
        self.variable_value = variable_value
        self.viewer_login = viewer_login
        self.created = None
        self.upserts = []

    def get_repo_variable(self, owner: str, repo: str, name: str):
        return self.variable_value

    def get_gist(self, gist_id: str):
        if self.gist and self.gist["id"] == gist_id:
            return self.gist
        return None

    def create_gist(self, description: str, public: bool):
        self.created = {
            "id": "created-gist",
            "html_url": "https://gist.github.com/created-gist",
            "owner": {"login": self.viewer_login},
        }
        return self.created

    def upsert_repo_variable(self, owner: str, repo: str, name: str, value: str) -> None:
        self.upserts.append((owner, repo, name, value))

    def get_authenticated_login(self) -> str:
        return self.viewer_login


def test_collect_sync_files_only_includes_expected_outputs(tmp_path: Path) -> None:
    (tmp_path / "list.txt").write_text("list", encoding="utf-8")
    (tmp_path / "list.meta.yml").write_text("meta", encoding="utf-8")
    (tmp_path / "README.md").write_text("ignore", encoding="utf-8")
    (tmp_path / "snippets").mkdir()
    (tmp_path / "snippets" / "nodes.yml").write_text("nodes", encoding="utf-8")
    (tmp_path / "snippets" / "notes.txt").write_text("skip", encoding="utf-8")
    (tmp_path / "artifacts" / "quality").mkdir(parents=True)
    (tmp_path / "artifacts" / "quality" / "summary.md").write_text("summary", encoding="utf-8")
    (tmp_path / "artifacts" / "local").mkdir(parents=True)
    (tmp_path / "artifacts" / "local" / "list.local.txt").write_text("local", encoding="utf-8")

    files = collect_sync_files(tmp_path, patterns=("list*", "snippets/**/*.yml", "artifacts/quality/*"))

    assert [path.as_posix() for path in files] == [
        "artifacts/quality/summary.md",
        "list.meta.yml",
        "list.txt",
        "snippets/nodes.yml",
    ]


def test_build_manifest_preserves_file_paths() -> None:
    manifest = build_manifest(
        repository="owner/repo",
        gist_id="gist-123",
        files=[Path("list.txt"), Path("snippets/nodes.yml")],
    )

    assert manifest["repository"] == "owner/repo"
    assert manifest["gist_id"] == "gist-123"
    assert manifest["file_count"] == 2
    assert manifest["files"] == ["list.txt", "snippets/nodes.yml"]


def test_ensure_gist_creates_and_persists_when_missing() -> None:
    client = FakeGitHubClient()

    gist = ensure_gist(
        client=client,
        repository="owner/repo",
        gist_id="",
        gist_id_variable="RESULT_GIST_ID",
        description="demo",
        public=False,
    )

    assert gist["id"] == "created-gist"
    assert client.upserts == [("owner", "repo", "RESULT_GIST_ID", "created-gist")]


def test_ensure_gist_uses_existing_variable_binding() -> None:
    client = FakeGitHubClient(
        gist={"id": "keep-gist", "html_url": "https://gist.github.com/keep-gist", "owner": {"login": "owner"}},
        variable_value="keep-gist",
    )

    gist = ensure_gist(
        client=client,
        repository="owner/repo",
        gist_id="",
        gist_id_variable="RESULT_GIST_ID",
        description="demo",
        public=False,
    )

    assert gist["id"] == "keep-gist"
    assert client.created is None
    assert client.upserts == []


def test_ensure_gist_recreates_when_owner_mismatches_token() -> None:
    client = FakeGitHubClient(
        gist={"id": "wrong-gist", "html_url": "https://gist.github.com/wrong-gist", "owner": {"login": "other-user"}},
        variable_value="wrong-gist",
        viewer_login="owner",
    )

    gist = ensure_gist(
        client=client,
        repository="owner/repo",
        gist_id="",
        gist_id_variable="RESULT_GIST_ID",
        description="demo",
        public=False,
    )

    assert gist["id"] == "created-gist"
    assert client.upserts == [("owner", "repo", "RESULT_GIST_ID", "created-gist")]


def test_build_authenticated_git_url_embeds_token_as_password() -> None:
    url = build_authenticated_git_url("https://gist.github.com/abc123.git", "ghp_token")

    assert url == "https://x-access-token:ghp_token@gist.github.com/abc123.git"
