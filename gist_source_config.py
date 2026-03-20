from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Iterable


GIST_PATH_SEPARATOR = "_d_"

PRIVATE_INPUT_FILES = (
    "sources.list",
    "sources.fansiphone.whitelist.list",
    "config.yml",
    "abpwhite.txt",
    "snippets/_config.yml",
    "snippets/example.yml",
)

PUBLIC_SOURCE_PATTERNS = (
    "list.txt",
    "list.yml",
    "list.meta.yml",
    "snippets/adblock.yml",
    "snippets/direct.yml",
    "snippets/malware.yml",
    "snippets/proxy.yml",
    "snippets/region.yml",
    "snippets/rules.yml",
    "snippets/rules_online.yml",
    "snippets/nodes.yml",
    "snippets/nodes.meta.yml",
    "snippets/nodes_*.yml",
    "snippets/nodes_*.meta.yml",
)

PRIVATE_ARTIFACT_PATTERNS = (
    "list_raw.txt",
    "list_result.csv",
    "artifacts/quality/*",
)

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


def flatten_gist_path(relative: Path) -> str:
    parts = relative.as_posix().split("/")
    return GIST_PATH_SEPARATOR.join(part.replace("_", "__") for part in parts)


def matches_source_patterns(source: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch(source, pattern) for pattern in patterns)
