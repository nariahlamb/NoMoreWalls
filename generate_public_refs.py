#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping

import requests

from gist_source_config import KEY_SOURCES, PUBLIC_SOURCE_PATTERNS, matches_source_patterns


GIST_API_BASE = "https://api.github.com/gists"
DEFAULT_TOKEN_ENV = "GIST_TOKEN"
DEFAULT_OUT_DIR = ".tmp/public_refs"
DEFAULT_LOCAL_METADATA_FILE = ".tmp/gist-sync-metadata.json"
GITHUB_API_TIMEOUT_SECONDS = 30
GITHUB_API_RETRY_ATTEMPTS = 3


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate public reference files from a gist manifest.")
    parser.add_argument("--gist-id", default=os.environ.get("RESULT_GIST_ID", ""), help="Target gist id.")
    parser.add_argument("--token", default="", help="GitHub token (optional for public/secret gist access).")
    parser.add_argument("--token-env", default=DEFAULT_TOKEN_ENV, help="Environment variable for token.")
    parser.add_argument(
        "--local-metadata-file",
        default=os.environ.get("GIST_SYNC_METADATA_FILE", DEFAULT_LOCAL_METADATA_FILE),
        help="Local metadata emitted by sync_gist.py.",
    )
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Directory to write reference files.")
    return parser


def build_headers(token: str) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "NoMoreWalls-public-refs",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_with_retry(url: str, headers: Mapping[str, str]) -> requests.Response:
    for attempt in range(1, GITHUB_API_RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(url, headers=headers, timeout=GITHUB_API_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            if attempt < GITHUB_API_RETRY_ATTEMPTS:
                print(f"读取 {url} 异常，将在 {attempt} 秒后重试：{exc}")
                time.sleep(attempt)
                continue
            raise RuntimeError(f"读取 {url} 失败: {exc}") from exc
        if response.status_code < 500 or attempt == GITHUB_API_RETRY_ATTEMPTS:
            return response
        print(f"读取 {url} 失败（{response.status_code}），将在 {attempt} 秒后重试。")
        time.sleep(attempt)
    raise RuntimeError(f"读取 {url} 失败: 超出最大重试次数")


def fetch_gist(gist_id: str, token: str) -> Dict[str, Any]:
    url = f"{GIST_API_BASE}/{gist_id}"
    response = get_with_retry(url, headers=build_headers(token))
    if response.status_code != 200:
        raise RuntimeError(f"拉取 Gist 失败: {response.status_code} {response.text[:300]}")
    return response.json()


def load_manifest(gist: Mapping[str, Any], token: str) -> Dict[str, Any]:
    gist_files = gist.get("files") or {}
    manifest_file = gist_files.get("manifest.json")
    if not manifest_file:
        return {}
    raw_url = str(manifest_file.get("raw_url") or "")
    if not raw_url:
        return {}
    response = get_with_retry(raw_url, headers=build_headers(token))
    if response.status_code != 200:
        return {}
    try:
        return response.json()
    except json.JSONDecodeError:
        return {}


def load_local_metadata(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"读取本地公开引用元数据失败: {path}") from exc


def resolve_gist_inputs(gist_id: str, token: str, local_metadata_file: Path) -> tuple[Dict[str, Any], Dict[str, str]]:
    metadata = load_local_metadata(local_metadata_file)
    if metadata:
        metadata_gist_id = str(metadata.get("gist_id") or "").strip()
        if gist_id and metadata_gist_id and metadata_gist_id != gist_id:
            raise RuntimeError(f"本地公开引用元数据与当前 Gist ID 不一致: {metadata_gist_id} != {gist_id}")
        source_links = metadata.get("source_links")
        if not isinstance(source_links, dict):
            raise RuntimeError(f"本地公开引用元数据缺少 source_links: {local_metadata_file}")
        gist = {
            "id": metadata_gist_id or gist_id,
            "html_url": str(metadata.get("gist_url") or ""),
            "updated_at": str(metadata.get("updated_at") or ""),
        }
        return gist, {str(key): str(value) for key, value in source_links.items()}

    gist = fetch_gist(gist_id=gist_id, token=token)
    manifest = load_manifest(gist=gist, token=token)
    return gist, build_source_links(gist=gist, manifest=manifest)


def build_source_links(gist: Mapping[str, Any], manifest: Mapping[str, Any]) -> Dict[str, str]:
    gist_files = gist.get("files") or {}
    source_links: Dict[str, str] = {}

    manifest_files = manifest.get("files") if isinstance(manifest, dict) else None
    if isinstance(manifest_files, list):
        for entry in manifest_files:
            if not isinstance(entry, dict):
                continue
            source = str(entry.get("source") or "").strip()
            gist_name = str(entry.get("gist") or "").strip()
            if not source or not gist_name:
                continue
            file_info = gist_files.get(gist_name) or {}
            raw_url = str(file_info.get("raw_url") or "").strip()
            if raw_url:
                source_links[source] = raw_url

    if source_links:
        return dict(sorted(source_links.items()))

    return dict(sorted(source_links.items()))


def build_public_source_links(source_links: Mapping[str, str]) -> Dict[str, str]:
    public_links: Dict[str, str] = {}
    for source, url in source_links.items():
        if matches_source_patterns(source, PUBLIC_SOURCE_PATTERNS):
            public_links[source] = url
    return dict(sorted(public_links.items()))


def build_key_links(source_links: Mapping[str, str]) -> Dict[str, str]:
    links: Dict[str, str] = {}
    for key in KEY_SOURCES:
        url = source_links.get(key)
        if url:
            links[key] = url
    return links


def write_index(out_dir: Path, gist: Mapping[str, Any], source_links: Mapping[str, str], key_links: Mapping[str, str]) -> None:
    payload = {
        "gist_id": gist.get("id", ""),
        "gist_url": gist.get("html_url", ""),
        "updated_at": gist.get("updated_at", ""),
        "file_count": len(source_links),
        "links": source_links,
        "key_links": key_links,
    }
    (out_dir / "index.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_subscriptions_md(out_dir: Path, gist: Mapping[str, Any], key_links: Mapping[str, str]) -> None:
    lines: List[str] = []
    lines.append("# 公开引用订阅清单")
    lines.append("")
    lines.append(f"- Gist: {gist.get('html_url', '')}")
    lines.append(f"- Updated: {gist.get('updated_at', '')}")
    lines.append("")

    lines.append("## 主订阅")
    lines.append("")
    for source in ("list.txt", "list.yml", "list.meta.yml"):
        url = key_links.get(source)
        if url:
            lines.append(f"- {source}: {url}")
    lines.append("")

    lines.append("## 关键 Snippets")
    lines.append("")
    for source in (
        "snippets/nodes.yml",
        "snippets/nodes.meta.yml",
        "snippets/nodes_JP.yml",
        "snippets/nodes_US.yml",
        "snippets/nodes_GB.yml",
        "snippets/nodes_SG.yml",
        "snippets/nodes_TW.yml",
        "snippets/nodes_HK.yml",
    ):
        url = key_links.get(source)
        if url:
            lines.append(f"- {source}: {url}")

    (out_dir / "subscriptions.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    args = build_parser().parse_args()
    token = args.token.strip() or os.environ.get(args.token_env, "").strip()
    gist_id = args.gist_id.strip()
    local_metadata_file = Path(args.local_metadata_file)
    if not gist_id and not local_metadata_file.is_file():
        print("未提供 Gist ID，跳过公开引用文件生成。")
        return 0

    gist, source_links = resolve_gist_inputs(
        gist_id=gist_id,
        token=token,
        local_metadata_file=local_metadata_file,
    )
    public_links = build_public_source_links(source_links)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    key_links = build_key_links(public_links)
    write_index(out_dir=out_dir, gist=gist, source_links=public_links, key_links=key_links)
    write_subscriptions_md(out_dir=out_dir, gist=gist, key_links=key_links)

    print(f"Gist ID: {gist.get('id', '')}")
    print(f"链接总数: {len(public_links)}")
    print(f"关键链接数: {len(key_links)}")
    print(f"输出目录: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
