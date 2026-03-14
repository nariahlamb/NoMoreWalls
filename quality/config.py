from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

import yaml


DEFAULT_REPO_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yml"
DEFAULT_LOCAL_QUALITY_PATH = Path(__file__).resolve().parents[1] / "local_quality.yml"


def _merge_mapping(base: Mapping[str, Any], override: Mapping[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _merge_mapping(result[key], value)
        else:
            result[key] = value
    return result


def load_repo_categories(config_path: Optional[Path] = None) -> Dict[str, List[str]]:
    config_path = Path(config_path or DEFAULT_REPO_CONFIG_PATH)
    if not config_path.exists():
        return {}

    with config_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    categories = ((data.get("NoMoreWalls") or {}).get("categories")) or {}
    return {
        str(category): [str(keyword) for keyword in keywords or []]
        for category, keywords in categories.items()
    }


@dataclass(frozen=True)
class LocalQualityConfig:
    protocol_weights: Dict[str, float] = field(default_factory=dict)
    preferred_category_weights: Dict[str, float] = field(default_factory=dict)
    metadata_weights: Dict[str, float] = field(default_factory=dict)
    provenance_weights: Dict[str, float] = field(default_factory=dict)
    penalties: Dict[str, float] = field(default_factory=dict)
    suspicious_keywords: List[str] = field(default_factory=list)
    banned_keywords: List[str] = field(default_factory=list)
    repo_categories: Dict[str, List[str]] = field(default_factory=dict)
    max_category_bonus: float = 6.0

    @classmethod
    def default(cls, repo_categories: Optional[Dict[str, List[str]]] = None) -> "LocalQualityConfig":
        return cls(
            protocol_weights={
                "hysteria2": 16.0,
                "hy2": 16.0,
                "tuic": 15.0,
                "vless-reality": 14.0,
                "vless": 11.0,
                "trojan": 9.0,
                "vmess": 7.0,
                "ss": 4.0,
                "ssr": 2.5,
            },
            preferred_category_weights={
                "HK": 2.8,
                "JP": 2.6,
                "SG": 2.4,
                "US": 2.2,
                "TW": 1.8,
                "IEPL": 2.5,
                "BGP": 1.5,
                "GPT": 1.2,
                "流媒体": 0.8,
            },
            metadata_weights={
                "server_present": 1.0,
                "valid_port": 1.0,
                "has_credentials": 2.2,
                "has_tls_hint": 1.6,
                "descriptive_name": 0.8,
                "client_compatibility": 1.0,
            },
            provenance_weights={
                "single_source": 0.6,
                "multi_source_bonus": 2.4,
                "extra_source_bonus": 0.7,
                "source_name_bonus": 0.3,
            },
            penalties={
                "broken_metadata": -4.0,
                "fake_keyword": -3.5,
                "banned_keyword": -12.0,
                "suspicious_endpoint": -5.0,
                "duplicate_conflict": -3.0,
                "cap_category_bonus": 6.0,
            },
            suspicious_keywords=[
                "free",
                "demo",
                "test",
                "expire",
                "traffic",
                "trial",
                "public",
                "wifi",
                "guest",
                "shared",
            ],
            banned_keywords=[
                "expired",
                "banned",
                "block",
                "forbidden",
                "spam",
            ],
            repo_categories=repo_categories or {},
            max_category_bonus=6.0,
        )

    @classmethod
    def from_dict(
        cls,
        data: Optional[Mapping[str, Any]],
        repo_categories: Optional[Dict[str, List[str]]] = None,
    ) -> "LocalQualityConfig":
        base = cls.default(repo_categories=repo_categories)
        if not data:
            return base

        merged = _merge_mapping(
            {
                "protocol_weights": base.protocol_weights,
                "preferred_category_weights": base.preferred_category_weights,
                "metadata_weights": base.metadata_weights,
                "provenance_weights": base.provenance_weights,
                "penalties": base.penalties,
                "suspicious_keywords": base.suspicious_keywords,
                "banned_keywords": base.banned_keywords,
                "repo_categories": base.repo_categories,
                "max_category_bonus": base.max_category_bonus,
            },
            data,
        )
        return cls(
            protocol_weights={str(k): float(v) for k, v in merged["protocol_weights"].items()},
            preferred_category_weights={
                str(k): float(v) for k, v in merged["preferred_category_weights"].items()
            },
            metadata_weights={str(k): float(v) for k, v in merged["metadata_weights"].items()},
            provenance_weights={
                str(k): float(v) for k, v in merged["provenance_weights"].items()
            },
            penalties={str(k): float(v) for k, v in merged["penalties"].items()},
            suspicious_keywords=[str(item).lower() for item in merged["suspicious_keywords"]],
            banned_keywords=[str(item).lower() for item in merged["banned_keywords"]],
            repo_categories={
                str(category): [str(keyword) for keyword in keywords or []]
                for category, keywords in merged["repo_categories"].items()
            },
            max_category_bonus=float(merged["max_category_bonus"]),
        )


def load_local_quality_config(
    path: Optional[Path] = None,
    *,
    overrides: Optional[Mapping[str, Any]] = None,
    repo_config_path: Optional[Path] = None,
) -> LocalQualityConfig:
    repo_categories = load_repo_categories(repo_config_path)
    data: Dict[str, Any] = {}
    path = Path(path or DEFAULT_LOCAL_QUALITY_PATH)
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or {}
        if isinstance(loaded, Mapping):
            data = dict(loaded)
    if overrides:
        data = _merge_mapping(data, overrides)
    return LocalQualityConfig.from_dict(data, repo_categories=repo_categories)
