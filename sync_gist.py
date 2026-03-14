#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests


DEFAULT_PATTERNS = (
    "list*",
    "snippets/**/*.yml",
    "artifacts/quality/*",
)
DEFAULT_GIST_ID_VARIABLE = "RESULT_GIST_ID"
DEFAULT_DESCRIPTION = "NoMoreWalls generated outputs"


class GitHubApiError(RuntimeError):
    pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync generated outputs to a single GitHub Gist.")
    parser.add_argument("--repo-root", default=".", help="Repository root to collect outputs from.")
    parser.add_argument(
        "--pattern",
        action="append",
        dest="patterns",
        help="Glob pattern to include. Can be repeated. Defaults to built-in output globs.",
    )
    parser.add_argument("--token", default="", help="GitHub token with gist + repo scopes.")
    parser.add_argument("--token-env", default="GIST_TOKEN", help="Environment variable to read token from.")
    parser.add_argument("--gist-id", default="", help="Existing gist id. If missing, resolve or create one.")
    parser.add_argument(
        "--gist-id-variable",
        default=DEFAULT_GIST_ID_VARIABLE,
        help="Repository Actions variable used to persist the gist id.",
    )
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""), help="owner/repo")
    parser.add_argument(
        "--description",
        default=os.environ.get("GIST_SYNC_DESCRIPTION", DEFAULT_DESCRIPTION),
        help="Description for a newly created gist.",
    )
    parser.add_argument("--public", action="store_true", help="Create a public gist instead of a secret gist.")
    parser.add_argument("--dry-run", action="store_true", help="Prepare files but do not push.")
    return parser


def collect_sync_files(repo_root: Path, patterns: Sequence[str]) -> List[Path]:
    selected: Dict[str, Path] = {}
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            relative = path.relative_to(repo_root)
            selected[relative.as_posix()] = relative
    return [selected[key] for key in sorted(selected)]


def build_manifest(repository: str, gist_id: str, files: Sequence[Path]) -> Dict[str, Any]:
    return {
        "repository": repository,
        "gist_id": gist_id,
        "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "file_count": len(files),
        "files": [path.as_posix() for path in files],
    }


def split_repository(repository: str) -> Tuple[str, str]:
    parts = repository.strip().split("/", 1)
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f"invalid repository: {repository!r}")
    return parts[0], parts[1]


def maybe_split_repository(repository: str) -> Tuple[str, str]:
    repository = repository.strip()
    if not repository:
        return "", ""
    return split_repository(repository)


def build_git_auth_header(token: str) -> str:
    raw = f"x-access-token:{token}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"Authorization: Basic {encoded}"


def run_git(args: Sequence[str], cwd: Optional[Path] = None, auth_header: str = "") -> subprocess.CompletedProcess[str]:
    cmd = ["git"]
    if auth_header:
        cmd.extend(["-c", f"http.extraHeader={auth_header}"])
    cmd.extend(args)
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )


class GitHubClient:
    def __init__(self, token: str, session: Optional[requests.Session] = None) -> None:
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "User-Agent": "NoMoreWalls-gist-sync",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def _request(self, method: str, url: str, expected: Sequence[int], **kwargs: Any) -> requests.Response:
        response = self.session.request(method, url, **kwargs)
        if response.status_code not in expected:
            raise GitHubApiError(
                f"{method} {url} failed: {response.status_code} {response.text[:400]}"
            )
        return response

    def get_repo_variable(self, owner: str, repo: str, name: str) -> Optional[str]:
        url = f"https://api.github.com/repos/{owner}/{repo}/actions/variables/{name}"
        response = self.session.get(url)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise GitHubApiError(f"GET {url} failed: {response.status_code} {response.text[:400]}")
        return response.json().get("value")

    def upsert_repo_variable(self, owner: str, repo: str, name: str, value: str) -> None:
        update_url = f"https://api.github.com/repos/{owner}/{repo}/actions/variables/{name}"
        payload = {"name": name, "value": value}
        response = self.session.patch(update_url, json=payload)
        if response.status_code == 404:
            create_url = f"https://api.github.com/repos/{owner}/{repo}/actions/variables"
            self._request("POST", create_url, expected=(201,), json=payload)
            return
        if response.status_code not in (204,):
            raise GitHubApiError(
                f"PATCH {update_url} failed: {response.status_code} {response.text[:400]}"
            )

    def get_gist(self, gist_id: str) -> Optional[Dict[str, Any]]:
        url = f"https://api.github.com/gists/{gist_id}"
        response = self.session.get(url)
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise GitHubApiError(f"GET {url} failed: {response.status_code} {response.text[:400]}")
        return response.json()

    def create_gist(self, description: str, public: bool) -> Dict[str, Any]:
        payload = {
            "description": description,
            "public": public,
            "files": {
                "README.md": {
                    "content": "This gist is managed automatically by NoMoreWalls GitHub Actions.\n"
                }
            },
        }
        response = self._request("POST", "https://api.github.com/gists", expected=(201,), json=payload)
        return response.json()


def ensure_gist(
    client: GitHubClient,
    repository: str,
    gist_id: str,
    gist_id_variable: str,
    description: str,
    public: bool,
) -> Dict[str, Any]:
    owner, repo = maybe_split_repository(repository)
    candidate = gist_id.strip()
    if not candidate and owner and repo:
        candidate = client.get_repo_variable(owner, repo, gist_id_variable) or ""

    gist: Optional[Dict[str, Any]] = None
    if candidate:
        gist = client.get_gist(candidate)

    if gist is None:
        gist = client.create_gist(description=description, public=public)
        if owner and repo:
            client.upsert_repo_variable(owner, repo, gist_id_variable, gist["id"])
        else:
            print("未提供 repository，已创建新 Gist，但不会自动回写仓库变量。")

    return gist


def reset_directory(path: Path) -> None:
    for child in path.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def stage_outputs(
    repo_root: Path,
    gist_root: Path,
    files: Sequence[Path],
    repository: str,
    gist_id: str,
) -> None:
    reset_directory(gist_root)
    for relative in files:
        target = gist_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(repo_root / relative, target)

    manifest = build_manifest(repository=repository, gist_id=gist_id, files=files)
    (gist_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def sync_gist_repo(
    repo_root: Path,
    files: Sequence[Path],
    gist: Dict[str, Any],
    token: str,
    repository: str,
    dry_run: bool,
) -> bool:
    auth_header = build_git_auth_header(token)
    clone_url = gist.get("git_pull_url") or f"https://gist.github.com/{gist['id']}.git"
    with tempfile.TemporaryDirectory(prefix="nomorewalls-gist-") as tempdir:
        gist_root = Path(tempdir) / "gist"
        run_git(["clone", "--depth", "1", clone_url, str(gist_root)], auth_header=auth_header)
        stage_outputs(repo_root=repo_root, gist_root=gist_root, files=files, repository=repository, gist_id=gist["id"])

        run_git(["config", "user.email", "actions@github.com"], cwd=gist_root)
        run_git(["config", "user.name", "GitHub Actions"], cwd=gist_root)
        run_git(["add", "--all"], cwd=gist_root)

        status = run_git(["status", "--porcelain"], cwd=gist_root).stdout.strip()
        if not status:
            print("Gist 内容无变化，跳过推送。")
            return False

        commit_message = datetime.datetime.now(datetime.timezone.utc).strftime("NoMoreWalls sync %Y-%m-%d %H:%M UTC")
        run_git(["commit", "-m", commit_message], cwd=gist_root)

        if dry_run:
            print("Dry run 已启用，已生成 Gist 工作区但未推送。")
            return True

        run_git(["push", "origin", "HEAD"], cwd=gist_root, auth_header=auth_header)
        return True


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    token = args.token.strip() or os.environ.get(args.token_env, "").strip()
    if not token:
        print(f"未检测到 {args.token_env}，跳过 Gist 同步。")
        return 0

    repo_root = Path(args.repo_root).resolve()
    patterns = tuple(args.patterns) if args.patterns else DEFAULT_PATTERNS
    files = collect_sync_files(repo_root=repo_root, patterns=patterns)
    if not files:
        print("没有找到可同步的输出文件，跳过。")
        return 0

    client = GitHubClient(token=token)
    gist = ensure_gist(
        client=client,
        repository=args.repository,
        gist_id=args.gist_id,
        gist_id_variable=args.gist_id_variable,
        description=args.description,
        public=args.public,
    )

    changed = sync_gist_repo(
        repo_root=repo_root,
        files=files,
        gist=gist,
        token=token,
        repository=args.repository,
        dry_run=args.dry_run,
    )

    print(f"Gist ID: {gist['id']}")
    print(f"Gist URL: {gist.get('html_url', '')}")
    print(f"同步文件数: {len(files)}")
    print(f"本次是否推送: {'是' if changed and not args.dry_run else '否'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
