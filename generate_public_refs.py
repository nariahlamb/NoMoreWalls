#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping

import requests


GIST_API_BASE = "https://api.github.com/gists"
GIST_PATH_SEPARATOR = "_d_"
DEFAULT_TOKEN_ENV = "GIST_TOKEN"
DEFAULT_OUT_DIR = "public_refs"

KEY_SOURCES = (
    "list.txt",
    "list.yml",
    "list.meta.yml",
    "snippets/nodes.yml",
    "snippets/nodes.meta.yml",
    "snippets/nodes_JP.yml",
    "snippets/nodes_JP.meta.yml",
    "snippets/nodes_US.yml",
    "snippets/nodes_US.meta.yml",
    "snippets/nodes_GB.yml",
    "snippets/nodes_GB.meta.yml",
    "snippets/nodes_SG.yml",
    "snippets/nodes_SG.meta.yml",
    "snippets/nodes_TW.yml",
    "snippets/nodes_TW.meta.yml",
    "snippets/nodes_HK.yml",
    "snippets/nodes_HK.meta.yml",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate public reference files from a gist manifest.")
    parser.add_argument("--gist-id", default=os.environ.get("RESULT_GIST_ID", ""), help="Target gist id.")
    parser.add_argument("--token", default="", help="GitHub token (optional for public/secret gist access).")
    parser.add_argument("--token-env", default=DEFAULT_TOKEN_ENV, help="Environment variable for token.")
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


def fetch_gist(gist_id: str, token: str) -> Dict[str, Any]:
    url = f"{GIST_API_BASE}/{gist_id}"
    response = requests.get(url, headers=build_headers(token), timeout=30)
    if response.status_code != 200:
        raise RuntimeError(f"拉取 Gist 失败: {response.status_code} {response.text[:300]}")
    return response.json()


def unflatten_gist_path(name: str) -> str:
    parts = name.split(GIST_PATH_SEPARATOR)
    return "/".join(part.replace("__", "_") for part in parts)


def load_manifest(gist: Mapping[str, Any], token: str) -> Dict[str, Any]:
    gist_files = gist.get("files") or {}
    manifest_file = gist_files.get("manifest.json")
    if not manifest_file:
        return {}
    raw_url = str(manifest_file.get("raw_url") or "")
    if not raw_url:
        return {}
    response = requests.get(raw_url, headers=build_headers(token), timeout=30)
    if response.status_code != 200:
        return {}
    try:
        return response.json()
    except json.JSONDecodeError:
        return {}


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

    # Fallback: manifest 缺失时尝试直接还原路径
    for gist_name, file_info in gist_files.items():
        if gist_name == "manifest.json":
            continue
        raw_url = str((file_info or {}).get("raw_url") or "").strip()
        if not raw_url:
            continue
        source_links[unflatten_gist_path(gist_name)] = raw_url

    return dict(sorted(source_links.items()))


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
    if not gist_id:
        print("未提供 Gist ID，跳过公开引用文件生成。")
        return 0

    gist = fetch_gist(gist_id=gist_id, token=token)
    manifest = load_manifest(gist=gist, token=token)
    source_links = build_source_links(gist=gist, manifest=manifest)

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    key_links = build_key_links(source_links)
    write_index(out_dir=out_dir, gist=gist, source_links=source_links, key_links=key_links)
    write_subscriptions_md(out_dir=out_dir, gist=gist, key_links=key_links)

    print(f"Gist ID: {gist.get('id', '')}")
    print(f"链接总数: {len(source_links)}")
    print(f"关键链接数: {len(key_links)}")
    print(f"输出目录: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
