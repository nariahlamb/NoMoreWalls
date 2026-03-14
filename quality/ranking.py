from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

from quality.models import ProbeResult, RankedNode


@dataclass(frozen=True)
class FilterReason:
    node_hash: str
    name: str
    reason_code: str
    reason: str


def _active_probe_score(
    probe_result: Optional[ProbeResult],
    *,
    latency_reference_ms: float,
    failure_penalty: float,
) -> float:
    if probe_result is None:
        return 0.0
    if not probe_result.ok:
        return -abs(failure_penalty)
    latency = float(probe_result.latency_ms or latency_reference_ms)
    if latency <= 0:
        latency = 1.0
    score = max(0.0, (latency_reference_ms - min(latency, latency_reference_ms)) / latency_reference_ms)
    return score * 100.0


def combine_rank_scores(
    ranked_nodes: Sequence[RankedNode],
    probe_results: Mapping[str, ProbeResult],
    ranking_config: Mapping[str, object],
) -> list[RankedNode]:
    passive_weight = float(ranking_config.get("passive_weight", 0.65))
    active_weight = float(ranking_config.get("active_weight", 0.35))
    latency_reference_ms = float(ranking_config.get("latency_reference_ms", 500.0))
    failure_penalty = float(ranking_config.get("failure_penalty", 8.0))

    combined: list[RankedNode] = []
    for item in ranked_nodes:
        probe_result = probe_results.get(item.snapshot.node_hash)
        active_score = _active_probe_score(
            probe_result,
            latency_reference_ms=latency_reference_ms,
            failure_penalty=failure_penalty,
        )
        final_score = round((item.passive_score.total * passive_weight) + (active_score * active_weight), 4)
        combined.append(
            RankedNode(
                snapshot=item.snapshot,
                passive_score=item.passive_score,
                final_score=final_score,
                rank=item.rank,
                probe_result=probe_result,
            )
        )

    combined.sort(
        key=lambda candidate: (
            candidate.final_score,
            candidate.passive_score.total,
            candidate.snapshot.source_count,
            candidate.snapshot.name.lower(),
        ),
        reverse=True,
    )
    return [
        RankedNode(
            snapshot=item.snapshot,
            passive_score=item.passive_score,
            final_score=item.final_score,
            rank=index,
            probe_result=item.probe_result,
        )
        for index, item in enumerate(combined, start=1)
    ]


def _node_region(node: RankedNode) -> str:
    if node.passive_score.matched_categories:
        return node.passive_score.matched_categories[0]
    if node.snapshot.categories:
        return node.snapshot.categories[0]
    return "UNKNOWN"


def _node_source(node: RankedNode) -> str:
    if node.snapshot.source_ids:
        return node.snapshot.source_ids[0]
    return "unknown"


def select_ranked_nodes(
    ranked_nodes: Sequence[RankedNode],
    ranking_config: Mapping[str, object],
) -> Tuple[list[RankedNode], list[FilterReason]]:
    max_nodes = int(ranking_config.get("max_nodes", 200))
    per_region_cap = int(ranking_config.get("per_region_cap", 40))
    max_per_source = int(ranking_config.get("max_per_source", 60))
    min_source_diversity = int(ranking_config.get("min_source_diversity", 8))

    region_caps_raw = ranking_config.get("region_caps") or {}
    if isinstance(region_caps_raw, Mapping):
        region_caps = {str(key): int(value) for key, value in region_caps_raw.items()}
    else:
        region_caps = {}

    by_source: Dict[str, list[RankedNode]] = {}
    for node in ranked_nodes:
        by_source.setdefault(_node_source(node), []).append(node)

    selected: list[RankedNode] = []
    selected_hashes: set[str] = set()
    reasons: list[FilterReason] = []
    source_count: Dict[str, int] = {}
    region_count: Dict[str, int] = {}

    source_heads = [nodes[0] for nodes in by_source.values() if nodes]
    source_heads.sort(key=lambda node: node.final_score, reverse=True)
    for node in source_heads:
        if len(selected) >= max_nodes or len(source_count) >= min_source_diversity:
            break
        region = _node_region(node)
        source = _node_source(node)
        region_cap = region_caps.get(region, per_region_cap)
        if region_count.get(region, 0) >= region_cap:
            reasons.append(
                FilterReason(
                    node_hash=node.snapshot.node_hash,
                    name=node.snapshot.name,
                    reason_code="region_cap",
                    reason=f"region {region} reached cap {region_cap}",
                )
            )
            continue
        selected.append(node)
        selected_hashes.add(node.snapshot.node_hash)
        source_count[source] = source_count.get(source, 0) + 1
        region_count[region] = region_count.get(region, 0) + 1

    for node in ranked_nodes:
        if len(selected) >= max_nodes:
            reasons.append(
                FilterReason(
                    node_hash=node.snapshot.node_hash,
                    name=node.snapshot.name,
                    reason_code="capacity",
                    reason=f"max_nodes={max_nodes}",
                )
            )
            continue
        if node.snapshot.node_hash in selected_hashes:
            continue

        source = _node_source(node)
        region = _node_region(node)
        region_cap = region_caps.get(region, per_region_cap)

        if source_count.get(source, 0) >= max_per_source:
            reasons.append(
                FilterReason(
                    node_hash=node.snapshot.node_hash,
                    name=node.snapshot.name,
                    reason_code="source_cap",
                    reason=f"source {source} reached cap {max_per_source}",
                )
            )
            continue
        if region_count.get(region, 0) >= region_cap:
            reasons.append(
                FilterReason(
                    node_hash=node.snapshot.node_hash,
                    name=node.snapshot.name,
                    reason_code="region_cap",
                    reason=f"region {region} reached cap {region_cap}",
                )
            )
            continue

        selected.append(node)
        selected_hashes.add(node.snapshot.node_hash)
        source_count[source] = source_count.get(source, 0) + 1
        region_count[region] = region_count.get(region, 0) + 1

    selected.sort(key=lambda node: node.final_score, reverse=True)
    selected = [
        RankedNode(
            snapshot=node.snapshot,
            passive_score=node.passive_score,
            final_score=node.final_score,
            rank=index,
            probe_result=node.probe_result,
        )
        for index, node in enumerate(selected, start=1)
    ]

    selected_hashes = {item.snapshot.node_hash for item in selected}
    for node in ranked_nodes:
        if node.snapshot.node_hash in selected_hashes:
            continue
        if any(item.node_hash == node.snapshot.node_hash for item in reasons):
            continue
        reasons.append(
            FilterReason(
                node_hash=node.snapshot.node_hash,
                name=node.snapshot.name,
                reason_code="lower_score",
                reason="filtered by ranking order",
            )
        )

    return selected, reasons
