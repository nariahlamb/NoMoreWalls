from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional


def _compact_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compute_node_hash(
    protocol: str,
    server: str,
    port: int,
    payload: Optional[Mapping[str, Any]] = None,
) -> str:
    payload = payload or {}
    keys = (
        "uuid",
        "id",
        "password",
        "cipher",
        "method",
        "network",
        "security",
        "sni",
        "servername",
        "host",
        "peer",
        "flow",
        "obfs",
        "protocol",
    )
    identity = {
        "protocol": (protocol or "").strip().lower(),
        "server": (server or "").strip().lower(),
        "port": int(port or 0),
    }
    for key in keys:
        value = payload.get(key)
        if value not in (None, "", [], {}):
            identity[key] = value
    return hashlib.sha256(_compact_json(identity).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class NodeProvenance:
    source_id: str
    source_name: str = ""
    raw_name: str = ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NodeProvenance":
        return cls(
            source_id=str(data.get("source_id", "")),
            source_name=str(data.get("source_name", "")),
            raw_name=str(data.get("raw_name", "")),
        )

    def to_dict(self) -> Dict[str, str]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "raw_name": self.raw_name,
        }


@dataclass(frozen=True)
class NodeSnapshot:
    node_hash: str
    protocol: str
    server: str
    port: int
    name: str
    raw_name: str
    source_ids: List[str] = field(default_factory=list)
    source_names: List[str] = field(default_factory=list)
    merged_at: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    provenance: List[NodeProvenance] = field(default_factory=list)
    supports_clash: bool = True
    supports_meta: bool = True
    supports_ray: bool = False
    categories: List[str] = field(default_factory=list)

    @property
    def source_count(self) -> int:
        return len(self.source_ids)

    @property
    def primary_source_id(self) -> str:
        return self.source_ids[0] if self.source_ids else ""

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "NodeSnapshot":
        payload = dict(data.get("payload") or {})
        provenance_data = data.get("provenance") or []
        source_ids = [str(item) for item in data.get("source_ids") or []]
        source_names = [str(item) for item in data.get("source_names") or []]

        provenance: List[NodeProvenance] = [
            NodeProvenance.from_dict(item)
            for item in provenance_data
            if isinstance(item, Mapping)
        ]
        if not provenance and source_ids:
            raw_name = str(data.get("raw_name", ""))
            provenance = [
                NodeProvenance(
                    source_id=source_id,
                    source_name=source_names[index] if index < len(source_names) else "",
                    raw_name=raw_name,
                )
                for index, source_id in enumerate(source_ids)
            ]

        node_hash = str(data.get("node_hash") or "")
        protocol = str(data.get("protocol", "")).lower()
        server = str(data.get("server", ""))
        port = int(data.get("port") or 0)
        if not node_hash:
            node_hash = compute_node_hash(protocol=protocol, server=server, port=port, payload=payload)

        return cls(
            node_hash=node_hash,
            protocol=protocol,
            server=server,
            port=port,
            name=str(data.get("name", "")),
            raw_name=str(data.get("raw_name", "")),
            source_ids=source_ids,
            source_names=source_names,
            merged_at=str(data.get("merged_at", "")),
            payload=payload,
            provenance=provenance,
            supports_clash=bool(data.get("supports_clash", True)),
            supports_meta=bool(data.get("supports_meta", True)),
            supports_ray=bool(data.get("supports_ray", False)),
            categories=[str(item) for item in data.get("categories") or []],
        )

    @classmethod
    def from_json_line(cls, line: str) -> "NodeSnapshot":
        return cls.from_dict(json.loads(line))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_hash": self.node_hash,
            "protocol": self.protocol,
            "server": self.server,
            "port": self.port,
            "name": self.name,
            "raw_name": self.raw_name,
            "source_ids": list(self.source_ids),
            "source_names": list(self.source_names),
            "merged_at": self.merged_at,
            "payload": dict(self.payload),
            "provenance": [item.to_dict() for item in self.provenance],
            "supports_clash": self.supports_clash,
            "supports_meta": self.supports_meta,
            "supports_ray": self.supports_ray,
            "categories": list(self.categories),
        }

    def to_json_line(self) -> str:
        return _compact_json(self.to_dict())


@dataclass(frozen=True)
class PassiveScore:
    node_hash: str
    total: float
    breakdown: Dict[str, float]
    matched_categories: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PassiveScore":
        breakdown = {
            str(key): float(value)
            for key, value in (data.get("breakdown") or {}).items()
        }
        total = data.get("total")
        if total is None:
            total = round(sum(breakdown.values()), 4)
        return cls(
            node_hash=str(data.get("node_hash", "")),
            total=float(total),
            breakdown=breakdown,
            matched_categories=[str(item) for item in data.get("matched_categories") or []],
            reasons=[str(item) for item in data.get("reasons") or []],
            flags=[str(item) for item in data.get("flags") or []],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_hash": self.node_hash,
            "total": self.total,
            "breakdown": dict(self.breakdown),
            "matched_categories": list(self.matched_categories),
            "reasons": list(self.reasons),
            "flags": list(self.flags),
        }


@dataclass(frozen=True)
class ProbeResult:
    node_hash: str
    ok: bool
    checked_at: str
    latency_ms: Optional[float] = None
    failure_reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProbeResult":
        latency = data.get("latency_ms")
        return cls(
            node_hash=str(data.get("node_hash", "")),
            ok=bool(data.get("ok", False)),
            checked_at=str(data.get("checked_at", "")),
            latency_ms=None if latency is None else float(latency),
            failure_reason=str(data.get("failure_reason", "")),
            details=dict(data.get("details") or {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_hash": self.node_hash,
            "ok": self.ok,
            "checked_at": self.checked_at,
            "latency_ms": self.latency_ms,
            "failure_reason": self.failure_reason,
            "details": dict(self.details),
        }


@dataclass
class RankedNode:
    snapshot: NodeSnapshot
    passive_score: PassiveScore
    final_score: float
    rank: int = 0
    probe_result: Optional[ProbeResult] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot": self.snapshot.to_dict(),
            "passive_score": self.passive_score.to_dict(),
            "final_score": self.final_score,
            "rank": self.rank,
            "probe_result": None if self.probe_result is None else self.probe_result.to_dict(),
        }


def load_snapshot_jsonl(lines: Iterable[str]) -> List[NodeSnapshot]:
    return [NodeSnapshot.from_json_line(line) for line in lines if line.strip()]
