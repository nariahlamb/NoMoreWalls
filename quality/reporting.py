from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Sequence

from quality.models import RankedNode
from quality.ranking import FilterReason


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_quality_reports(
    quality_dir: Path,
    ranked_nodes: Sequence[RankedNode],
    selected_nodes: Sequence[RankedNode],
    filter_reasons: Sequence[FilterReason],
) -> Dict[str, str]:
    quality_dir.mkdir(parents=True, exist_ok=True)

    top_nodes_path = quality_dir / "top_nodes.csv"
    with top_nodes_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "node_hash", "name", "protocol", "server", "source_count", "passive_score", "final_score", "latency_ms"])
        for node in selected_nodes:
            writer.writerow(
                [
                    node.rank,
                    node.snapshot.node_hash,
                    node.snapshot.name,
                    node.snapshot.protocol,
                    node.snapshot.server,
                    node.snapshot.source_count,
                    node.passive_score.total,
                    node.final_score,
                    "" if not node.probe_result else (node.probe_result.latency_ms or ""),
                ]
            )

    filter_reasons_path = quality_dir / "filter_reasons.csv"
    with filter_reasons_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["node_hash", "name", "reason_code", "reason"])
        for item in filter_reasons:
            writer.writerow([item.node_hash, item.name, item.reason_code, item.reason])

    source_totals: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0.0, "selected": 0.0, "score_sum": 0.0})
    selected_hashes = {node.snapshot.node_hash for node in selected_nodes}
    for node in ranked_nodes:
        source_id = node.snapshot.primary_source_id or "unknown"
        source_totals[source_id]["count"] += 1
        source_totals[source_id]["score_sum"] += node.final_score
        if node.snapshot.node_hash in selected_hashes:
            source_totals[source_id]["selected"] += 1

    source_reputation_path = quality_dir / "source_reputation.csv"
    with source_reputation_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_id", "total_nodes", "selected_nodes", "selected_ratio", "avg_final_score"])
        for source_id, stats in sorted(source_totals.items(), key=lambda pair: pair[0]):
            total_nodes = int(stats["count"])
            selected_nodes_count = int(stats["selected"])
            selected_ratio = round((selected_nodes_count / total_nodes), 4) if total_nodes else 0.0
            avg_score = round((stats["score_sum"] / total_nodes), 4) if total_nodes else 0.0
            writer.writerow([source_id, total_nodes, selected_nodes_count, selected_ratio, avg_score])

    summary_path = quality_dir / "summary.md"
    summary = [
        "# Local Node Quality Summary",
        "",
        f"- Generated At: {_utc_now_iso()}",
        f"- Total Ranked Nodes: {len(ranked_nodes)}",
        f"- Selected Nodes: {len(selected_nodes)}",
        f"- Filtered Nodes: {len(filter_reasons)}",
        "",
        "## Outputs",
        f"- top_nodes.csv: {top_nodes_path}",
        f"- filter_reasons.csv: {filter_reasons_path}",
        f"- source_reputation.csv: {source_reputation_path}",
    ]
    summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8", newline="\n")

    return {
        "summary": str(summary_path),
        "top_nodes": str(top_nodes_path),
        "filter_reasons": str(filter_reasons_path),
        "source_reputation": str(source_reputation_path),
    }
