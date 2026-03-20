from __future__ import annotations

from pathlib import Path

import pytest

from restore_gist_files import restore_files_from_directory, validate_gist_selection


def test_restore_files_from_directory_restores_flattened_paths(tmp_path: Path) -> None:
    gist_root = tmp_path / "gist"
    repo_root = tmp_path / "repo"
    gist_root.mkdir()
    repo_root.mkdir()
    (gist_root / "sources.list").write_text("source", encoding="utf-8")
    (gist_root / "snippets_d___config.yml").write_text("config", encoding="utf-8")

    restore_files_from_directory(
        gist_root=gist_root,
        repo_root=repo_root,
        files=("sources.list", "snippets/_config.yml"),
    )

    assert (repo_root / "sources.list").read_text(encoding="utf-8") == "source"
    assert (repo_root / "snippets" / "_config.yml").read_text(encoding="utf-8") == "config"


def test_restore_files_from_directory_raises_when_required_file_missing(tmp_path: Path) -> None:
    gist_root = tmp_path / "gist"
    repo_root = tmp_path / "repo"
    gist_root.mkdir()
    repo_root.mkdir()

    with pytest.raises(FileNotFoundError, match="config.yml"):
        restore_files_from_directory(gist_root=gist_root, repo_root=repo_root, files=("config.yml",))


def test_restore_files_from_directory_reports_flattened_gist_name(tmp_path: Path) -> None:
    gist_root = tmp_path / "gist"
    repo_root = tmp_path / "repo"
    gist_root.mkdir()
    repo_root.mkdir()

    with pytest.raises(FileNotFoundError, match=r"snippets_d___config\.yml -> snippets/_config\.yml"):
        restore_files_from_directory(gist_root=gist_root, repo_root=repo_root, files=("snippets/_config.yml",))


def test_validate_gist_selection_rejects_same_config_and_result_gist(monkeypatch) -> None:
    monkeypatch.setenv("RESULT_GIST_ID", "gist-123")

    with pytest.raises(RuntimeError, match=r"snippets_d___config\.yml -> snippets/_config\.yml"):
        validate_gist_selection("gist-123", "CONFIG_GIST_ID", "RESULT_GIST_ID")
