#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterable, Optional, Sequence

from gist_source_config import PRIVATE_INPUT_FILES, describe_gist_file, describe_gist_files, flatten_gist_path
from sync_gist import build_authenticated_git_url, run_git


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Restore private input files from a GitHub Gist.")
    parser.add_argument("--repo-root", default=".", help="Repository root to restore files into.")
    parser.add_argument("--gist-id", default="", help="Private config gist id.")
    parser.add_argument("--gist-id-env", default="CONFIG_GIST_ID", help="Environment variable containing gist id.")
    parser.add_argument(
        "--result-gist-id-env",
        default="RESULT_GIST_ID",
        help="Environment variable containing the public result gist id for validation.",
    )
    parser.add_argument("--token", default="", help="GitHub token with gist scope.")
    parser.add_argument("--token-env", default="GIST_TOKEN", help="Environment variable containing GitHub token.")
    parser.add_argument(
        "--file",
        action="append",
        dest="files",
        help="Relative file path to restore. Can be repeated. Defaults to the standard private input set.",
    )
    return parser


def restore_files_from_directory(gist_root: Path, repo_root: Path, files: Iterable[str]) -> None:
    for relative_name in files:
        relative = Path(relative_name)
        source = gist_root / flatten_gist_path(relative)
        if not source.is_file():
            raise FileNotFoundError(f"Gist 中缺少文件: {describe_gist_file(relative.as_posix())}")
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def restore_files(repo_root: Path, gist_id: str, token: str, files: Sequence[str]) -> None:
    clone_url = build_authenticated_git_url(f"https://gist.github.com/{gist_id}.git", token=token)
    with tempfile.TemporaryDirectory(prefix="nomorewalls-config-gist-") as tempdir:
        gist_root = Path(tempdir) / "gist"
        run_git(["clone", "--depth", "1", clone_url, str(gist_root)], redacted_values=(token,))
        restore_files_from_directory(gist_root=gist_root, repo_root=repo_root, files=files)


def resolve_arg_or_env(value: str, env_name: str) -> str:
    if value.strip():
        return value.strip()
    return str(os.environ.get(env_name, "")).strip()


def validate_gist_selection(gist_id: str, gist_id_env: str, result_gist_id_env: str) -> None:
    if not gist_id:
        raise RuntimeError(
            f"未提供 {gist_id_env}，无法恢复私有抓取配置。"
            f"当前 workflow 会从 vars.{gist_id_env} 或 secrets.{gist_id_env} 读取。"
        )
    result_gist_id = str(os.environ.get(result_gist_id_env, "")).strip()
    if result_gist_id and gist_id == result_gist_id:
        raise RuntimeError(
            f"{gist_id_env} 与 {result_gist_id_env} 不能指向同一个 Gist。"
            f"配置 Gist 必须包含以下 Gist 文件：{describe_gist_files(PRIVATE_INPUT_FILES)}。"
        )


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    gist_id = resolve_arg_or_env(args.gist_id, args.gist_id_env)
    token = resolve_arg_or_env(args.token, args.token_env)
    files = tuple(args.files) if args.files else PRIVATE_INPUT_FILES
    validate_gist_selection(gist_id, args.gist_id_env, args.result_gist_id_env)
    if not token:
        raise RuntimeError(f"未提供 {args.token_env}，无法恢复私有抓取配置。")
    restore_files(repo_root=repo_root, gist_id=gist_id, token=token, files=files)
    print(f"已恢复私有配置文件数: {len(files)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
