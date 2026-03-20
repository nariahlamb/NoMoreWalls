from __future__ import annotations

from pathlib import Path

import pytest

from restore_gist_files import restore_files_from_directory


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

    with pytest.raises(FileNotFoundError):
        restore_files_from_directory(gist_root=gist_root, repo_root=repo_root, files=("config.yml",))
