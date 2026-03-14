from __future__ import annotations

import csv
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence, Set

from quality.models import NodeProvenance, NodeSnapshot, compute_node_hash


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _utc_now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _source_label(source_id: Any, sources: Sequence[Any]) -> str:
    idx = _to_int(source_id, -1)
    if 0 <= idx < len(sources):
        return str(getattr(sources[idx], "url", ""))
    return ""


def _supports(node: Any, method_name: str, default: bool) -> bool:
    method = getattr(node, method_name, None)
    if method is None:
        return default
    try:
        return bool(method())
    except Exception:
        return default


def _match_categories(name: str, categories: Optional[Mapping[str, Sequence[str]]]) -> list[str]:
    if not categories:
        return []
    matched: list[str] = []
    lower_name = (name or "").lower()
    for category, keywords in categories.items():
        for keyword in keywords or []:
            text = str(keyword or "").lower()
            if not text:
                continue
            if text in lower_name:
                matched.append(str(category))
                break
    return matched


def build_snapshot_record(
    node: Any,
    source_names_by_id: Mapping[str, str],
    raw_names_by_source_id: Mapping[str, str],
    merged_at: str,
    categories: Optional[Mapping[str, Sequence[str]]] = None,
) -> NodeSnapshot:
    payload: Dict[str, Any] = dict(getattr(node, "data", {}) or {})
    protocol = str(getattr(node, "type", payload.get("type", "")) or "").lower()
    server = str(payload.get("server", "") or "")
    port = _to_int(payload.get("port"), 0)
    payload["type"] = protocol
    payload["server"] = server
    payload["port"] = port
    normalized_name = str(payload.get("name", "") or "")

    ordered_items = sorted(
        raw_names_by_source_id.items(),
        key=lambda item: (_to_int(item[0], 10**9), str(item[0])),
    )
    source_ids: list[str] = [str(source_id) for source_id, _ in ordered_items]
    source_names: list[str] = [str(source_names_by_id.get(source_id, "")) for source_id in source_ids]
    provenance = [
        NodeProvenance(
            source_id=str(source_id),
            source_name=str(source_names_by_id.get(source_id, "")),
            raw_name=str(raw_name or ""),
        )
        for source_id, raw_name in ordered_items
    ]
    raw_name = next((item.raw_name for item in provenance if item.raw_name.strip()), normalized_name)
    node_hash = compute_node_hash(protocol=protocol, server=server, port=port, payload=payload)

    return NodeSnapshot(
        node_hash=node_hash,
        protocol=protocol,
        server=server,
        port=port,
        name=normalized_name,
        raw_name=raw_name,
        source_ids=source_ids,
        source_names=source_names,
        merged_at=merged_at,
        payload=payload,
        provenance=provenance,
        supports_clash=_supports(node, "supports_clash", True),
        supports_meta=_supports(node, "supports_meta", True),
        supports_ray=_supports(node, "supports_ray", False),
        categories=_match_categories(normalized_name or raw_name, categories),
    )


def build_snapshot_records(
    merged: Mapping[Any, Any],
    used: Mapping[Any, Mapping[Any, Any]],
    sources: Sequence[Any],
    *,
    categories: Optional[Mapping[str, Sequence[str]]] = None,
    merged_at: Optional[str] = None,
) -> list[NodeSnapshot]:
    timestamp = merged_at or _utc_now_iso()
    source_names_by_id = {str(index): str(getattr(source, "url", "")) for index, source in enumerate(sources)}

    snapshots: list[NodeSnapshot] = []
    for legacy_hash, node in merged.items():
        raw_map = used.get(legacy_hash) or {}
        raw_names_by_source_id = {str(source_id): str(raw_name) for source_id, raw_name in raw_map.items()}
        snapshots.append(
            build_snapshot_record(
                node=node,
                source_names_by_id=source_names_by_id,
                raw_names_by_source_id=raw_names_by_source_id,
                merged_at=timestamp,
                categories=categories,
            )
        )
    snapshots.sort(key=lambda item: item.node_hash)
    return snapshots


def _write_snapshot_jsonl(path: Path, records: Sequence[NodeSnapshot]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.to_json_line())
            handle.write("\n")


def _write_source_summary_csv(
    path: Path,
    sources: Sequence[Any],
    used: Mapping[Any, Mapping[Any, Any]],
) -> None:
    counts: Dict[str, int] = {}
    for source_map in used.values():
        for source_id in source_map:
            key = str(source_id)
            counts[key] = counts.get(key, 0) + 1

    known_ids = {str(i) for i in range(len(sources))}
    extra_ids = sorted(set(counts) - known_ids)
    rows = []
    for idx, source in enumerate(sources):
        sid = str(idx)
        rows.append(
            {
                "source_id": sid,
                "source_name": str(getattr(source, "url", "")),
                "merged_nodes": counts.get(sid, 0),
            }
        )
    for sid in extra_ids:
        rows.append({"source_id": sid, "source_name": "", "merged_nodes": counts[sid]})

    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_id", "source_name", "merged_nodes"])
        writer.writeheader()
        writer.writerows(rows)


def export_quality_artifacts(
    merged: Optional[Mapping[Any, Any]] = None,
    used: Optional[Mapping[Any, Mapping[Any, Any]]] = None,
    unknown: Optional[Set[Any]] = None,
    sources: Optional[Sequence[Any]] = None,
    *,
    output_dir: Path | str = Path("artifacts") / "quality",
    categories: Optional[Mapping[str, Sequence[str]]] = None,
    merged_at: Optional[str] = None,
    **legacy_kwargs: Any,
) -> Dict[str, str]:
    merged = merged or legacy_kwargs.get("merged_nodes") or {}
    used = used or legacy_kwargs.get("used_map") or {}
    unknown = unknown or legacy_kwargs.get("unknown_nodes") or set()
    sources = sources or legacy_kwargs.get("sources") or []

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = out_dir / "node_snapshot.jsonl"
    source_summary_path = out_dir / "source_summary.csv"
    merge_stats_path = out_dir / "merge_stats.json"
    unknown_nodes_path = out_dir / "unknown_nodes.txt"

    snapshots = build_snapshot_records(
        merged=merged,
        used=used,
        sources=sources,
        categories=categories,
        merged_at=merged_at,
    )
    _write_snapshot_jsonl(snapshot_path, snapshots)
    _write_source_summary_csv(source_summary_path, sources=sources, used=used)

    unknown_lines = sorted({str(item) for item in unknown if str(item).strip()})
    unknown_nodes_path.write_text("\n".join(unknown_lines), encoding="utf-8")

    supports_stats = {
        "supports_clash": sum(1 for item in snapshots if item.supports_clash),
        "supports_meta": sum(1 for item in snapshots if item.supports_meta),
        "supports_ray": sum(1 for item in snapshots if item.supports_ray),
    }
    stats: MutableMapping[str, Any] = {
        "generated_at": _utc_now_iso(),
        "total_merged": len(snapshots),
        "total_unknown": len(unknown_lines),
        "total_sources": len(sources),
        "supports": supports_stats,
    }
    merge_stats_path.write_text(
        json.dumps(dict(stats), ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "output_dir": str(out_dir),
        "snapshot": str(snapshot_path),
        "source_summary": str(source_summary_path),
        "merge_stats": str(merge_stats_path),
        "unknown_nodes": str(unknown_nodes_path),
    }
