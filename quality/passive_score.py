from __future__ import annotations

import re
from typing import Iterable, List, Optional, Sequence, Tuple

from quality.config import LocalQualityConfig, load_local_quality_config
from quality.models import NodeSnapshot, PassiveScore, RankedNode


_MULTISPACE = re.compile(r"\s+")


def _normalize_text(value: str) -> str:
    return _MULTISPACE.sub(" ", value or "").strip().lower()


def _protocol_key(snapshot: NodeSnapshot) -> str:
    payload = snapshot.payload or {}
    protocol = (snapshot.protocol or "").lower()
    if protocol == "hysteria2":
        return "hysteria2"
    if protocol == "hy2":
        return "hy2"
    if protocol == "vless":
        security = _normalize_text(str(payload.get("security", "")))
        flow = _normalize_text(str(payload.get("flow", "")))
        if "reality" in security or "vision" in flow or payload.get("public-key"):
            return "vless-reality"
    return protocol


def infer_categories(snapshot: NodeSnapshot, config: Optional[LocalQualityConfig] = None) -> List[str]:
    config = config or load_local_quality_config()
    if snapshot.categories:
        return list(dict.fromkeys(snapshot.categories))

    haystack = " ".join(
        [
            snapshot.name,
            snapshot.raw_name,
            snapshot.server,
            " ".join(snapshot.source_names),
        ]
    ).lower()
    matches: List[str] = []
    for category, keywords in config.repo_categories.items():
        for keyword in keywords:
            if keyword and str(keyword).lower() in haystack:
                matches.append(category)
                break
    return list(dict.fromkeys(matches))


def _has_credentials(snapshot: NodeSnapshot) -> bool:
    payload = snapshot.payload or {}
    for key in ("uuid", "id", "password", "token", "auth-str", "auth_str", "psk"):
        if payload.get(key):
            return True
    return False


def _has_tls_hint(snapshot: NodeSnapshot) -> bool:
    payload = snapshot.payload or {}
    for key in ("tls", "sni", "servername", "serverName", "peer", "public-key", "reality-opts"):
        value = payload.get(key)
        if isinstance(value, bool) and value:
            return True
        if value not in (None, "", [], {}):
            return True
    security = _normalize_text(str(payload.get("security", "")))
    return any(token in security for token in ("tls", "reality"))


def _looks_descriptive(name: str) -> bool:
    normalized = _normalize_text(name)
    if len(normalized) < 4:
        return False
    digit_count = sum(char.isdigit() for char in normalized)
    return digit_count <= max(4, len(normalized) // 2)


def _has_suspicious_endpoint(server: str) -> bool:
    normalized = _normalize_text(server)
    suspicious_tokens = ("0.0.0.0", "127.0.0.1", "localhost", "example.", ".invalid")
    return any(token in normalized for token in suspicious_tokens)


def score_snapshot(
    snapshot: NodeSnapshot,
    config: Optional[LocalQualityConfig] = None,
) -> PassiveScore:
    config = config or load_local_quality_config()
    payload = snapshot.payload or {}
    name_blob = " ".join([snapshot.name, snapshot.raw_name, " ".join(snapshot.source_names)])
    normalized_name_blob = _normalize_text(name_blob)
    matched_categories = infer_categories(snapshot, config=config)

    breakdown = {
        "protocol": 0.0,
        "provenance": 0.0,
        "metadata_quality": 0.0,
        "category_confidence": 0.0,
        "fake_risk_penalty": 0.0,
        "duplicate_conflict_penalty": 0.0,
    }
    reasons: List[str] = []
    flags: List[str] = []

    protocol_key = _protocol_key(snapshot)
    breakdown["protocol"] = config.protocol_weights.get(protocol_key, config.protocol_weights.get(snapshot.protocol, 0.0))
    reasons.append("protocol:%s" % protocol_key)

    source_count = max(1, snapshot.source_count or len(snapshot.provenance) or 0)
    provenance_score = config.provenance_weights.get("single_source", 0.0)
    if source_count >= 2:
        provenance_score += config.provenance_weights.get("multi_source_bonus", 0.0)
        provenance_score += (source_count - 2) * config.provenance_weights.get("extra_source_bonus", 0.0)
        reasons.append("provenance:multi_source")
    else:
        reasons.append("provenance:single_source")
    if any(item.source_name for item in snapshot.provenance):
        provenance_score += config.provenance_weights.get("source_name_bonus", 0.0)
    breakdown["provenance"] = provenance_score

    metadata_score = 0.0
    if snapshot.server:
        metadata_score += config.metadata_weights.get("server_present", 0.0)
    if 0 < snapshot.port <= 65535:
        metadata_score += config.metadata_weights.get("valid_port", 0.0)
    else:
        breakdown["fake_risk_penalty"] += config.penalties.get("broken_metadata", 0.0)
        flags.append("invalid_port")
    if _has_credentials(snapshot):
        metadata_score += config.metadata_weights.get("has_credentials", 0.0)
    else:
        breakdown["fake_risk_penalty"] += config.penalties.get("broken_metadata", 0.0)
        flags.append("missing_credentials")
    if _has_tls_hint(snapshot):
        metadata_score += config.metadata_weights.get("has_tls_hint", 0.0)
    if _looks_descriptive(snapshot.name):
        metadata_score += config.metadata_weights.get("descriptive_name", 0.0)
    if snapshot.supports_clash or snapshot.supports_meta or snapshot.supports_ray:
        metadata_score += config.metadata_weights.get("client_compatibility", 0.0)
    breakdown["metadata_quality"] = metadata_score

    category_bonus = 0.0
    for category in matched_categories:
        category_bonus += config.preferred_category_weights.get(category, 0.0)
    breakdown["category_confidence"] = min(category_bonus, config.max_category_bonus)
    if matched_categories:
        reasons.append("categories:%s" % ",".join(matched_categories))

    for keyword in config.suspicious_keywords:
        if keyword in normalized_name_blob:
            breakdown["fake_risk_penalty"] += config.penalties.get("fake_keyword", 0.0)
            flags.append("keyword:%s" % keyword)
    for keyword in config.banned_keywords:
        if keyword in normalized_name_blob:
            breakdown["fake_risk_penalty"] += config.penalties.get("banned_keyword", 0.0)
            flags.append("banned:%s" % keyword)
    if _has_suspicious_endpoint(snapshot.server):
        breakdown["fake_risk_penalty"] += config.penalties.get("suspicious_endpoint", 0.0)
        flags.append("suspicious_endpoint")

    if payload.get("duplicate_conflict") or payload.get("duplicate_conflict_count", 0):
        count = int(payload.get("duplicate_conflict_count") or 1)
        breakdown["duplicate_conflict_penalty"] = count * config.penalties.get("duplicate_conflict", 0.0)
        flags.append("duplicate_conflict")

    total = round(sum(breakdown.values()), 4)
    return PassiveScore(
        node_hash=snapshot.node_hash,
        total=total,
        breakdown={key: round(value, 4) for key, value in breakdown.items()},
        matched_categories=matched_categories,
        reasons=reasons,
        flags=list(dict.fromkeys(flags)),
    )


def score_many(
    snapshots: Iterable[NodeSnapshot],
    config: Optional[LocalQualityConfig] = None,
) -> List[Tuple[NodeSnapshot, PassiveScore]]:
    config = config or load_local_quality_config()
    return [(snapshot, score_snapshot(snapshot, config=config)) for snapshot in snapshots]


def rank_nodes_passively(
    snapshots: Sequence[NodeSnapshot],
    config: Optional[LocalQualityConfig] = None,
) -> List[RankedNode]:
    scored = score_many(snapshots, config=config)
    scored.sort(
        key=lambda item: (
            item[1].total,
            item[0].source_count,
            item[0].name.lower(),
        ),
        reverse=True,
    )
    ranked: List[RankedNode] = []
    for index, (snapshot, passive_score) in enumerate(scored, start=1):
        ranked.append(
            RankedNode(
                snapshot=snapshot,
                passive_score=passive_score,
                final_score=passive_score.total,
                rank=index,
            )
        )
    return ranked
