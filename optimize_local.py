#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import yaml

from quality.cache import ProbeCache
from quality.config import load_local_quality_config
from quality.models import NodeSnapshot, load_snapshot_jsonl
from quality.output_writer import write_local_outputs
from quality.passive_score import rank_nodes_passively
from quality.probe_runner import run_active_probe
from quality.ranking import combine_rank_scores, select_ranked_nodes
from quality.reporting import write_quality_reports


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return dict(loaded) if isinstance(loaded, Mapping) else {}


def _load_snapshot(snapshot_path: Path) -> List[NodeSnapshot]:
    lines = snapshot_path.read_text(encoding="utf-8").splitlines()
    return load_snapshot_jsonl(lines)


def _first_probe_url(probe_cfg: Mapping[str, Any]) -> str:
    urls = [str(item) for item in (probe_cfg.get("urls") or probe_cfg.get("targets") or []) if str(item)]
    if urls:
        return urls[0]
    return "https://www.gstatic.com/generate_204"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NoMoreWalls local node quality optimizer")
    parser.add_argument(
        "--config",
        "--quality-config",
        dest="config",
        default="local_quality.yml",
        help="Path to local quality config",
    )
    parser.add_argument("--artifacts-dir", default="artifacts", help="Base artifacts directory")
    parser.add_argument("--snapshot-path", default="", help="Override snapshot path")
    parser.add_argument("--snapshot-only", action="store_true", help="Validate and inspect snapshot only")
    parser.add_argument("--passive-only", action="store_true", help="Run passive scoring only")
    parser.add_argument("--full-probe", action="store_true", help="Run full active probe by Mihomo")
    parser.add_argument("--mihomo-path", default="", help="Mihomo executable path")
    parser.add_argument("--reuse-cache", action="store_true", help="Reuse existing probe cache entries")
    parser.add_argument("--clear-cache", action="store_true", help="Clear probe cache before probing")
    parser.add_argument("--report-only", action="store_true", help="Only regenerate reports")
    return parser


def run(argv: Optional[Iterable[str]] = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)

    config_path = Path(args.config)
    config_data = _load_yaml(config_path)
    artifacts_root = Path(args.artifacts_dir)
    artifacts_root.mkdir(parents=True, exist_ok=True)

    output_cfg = config_data.get("output") or {}
    quality_dir = artifacts_root / str(output_cfg.get("quality_subdir", "quality"))
    local_dir = artifacts_root / str(output_cfg.get("local_subdir", "local"))
    quality_dir.mkdir(parents=True, exist_ok=True)
    local_dir.mkdir(parents=True, exist_ok=True)

    snapshot_path = Path(args.snapshot_path) if args.snapshot_path else quality_dir / "node_snapshot.jsonl"
    if not snapshot_path.exists():
        print(f"Snapshot file not found: {snapshot_path}")
        print("Run `python fetch.py` first to export artifacts/quality/node_snapshot.jsonl")
        return 2

    snapshots = _load_snapshot(snapshot_path)
    print(f"Loaded snapshot nodes: {len(snapshots)}")
    if args.snapshot_only:
        print(f"Snapshot only mode completed: {snapshot_path}")
        return 0

    passive_config = load_local_quality_config(path=config_path)
    passive_ranked = rank_nodes_passively(snapshots, config=passive_config)

    probe_cfg = dict(config_data.get("probe") or {})
    ranking_cfg = dict(config_data.get("ranking") or {})
    cache_cfg = dict(config_data.get("cache") or {})

    probe_results = {}
    full_probe_enabled = bool(args.full_probe and not args.passive_only and not args.report_only)
    if full_probe_enabled:
        cache = ProbeCache(
            cache_path=Path(cache_cfg.get("probe_cache_path", "cache/local_quality/probe_cache.json")),
            session_state_path=Path(cache_cfg.get("session_state_path", "cache/local_quality/session_state.json")),
            history_path=Path(cache_cfg.get("history_path", str(quality_dir / "probe_history.jsonl"))),
            ttl_seconds=int(cache_cfg.get("ttl_seconds", 21600)),
        )
        try:
            probe_results = run_active_probe(
                passive_ranked,
                probe_cfg,
                template_path=str(output_cfg.get("template_path", "snippets/example.yml")),
                mihomo_path=args.mihomo_path or None,
                cache=cache,
                reuse_cache=args.reuse_cache,
                clear_cache=args.clear_cache,
            )
            print(f"Active probe finished: {len(probe_results)} results")
        except FileNotFoundError:
            print("Mihomo not available, fallback to passive-only ranking")

    combined_ranked = combine_rank_scores(passive_ranked, probe_results, ranking_cfg)
    selected_nodes, filter_reasons = select_ranked_nodes(combined_ranked, ranking_cfg)

    if not args.report_only:
        output_paths = write_local_outputs(
            artifacts_dir=artifacts_root,
            ranked_nodes=selected_nodes,
            probe_url=_first_probe_url(probe_cfg),
        )
        print("Local outputs:")
        print(json.dumps(output_paths.as_dict(), ensure_ascii=False, indent=2))

    report_paths = write_quality_reports(
        quality_dir=quality_dir,
        ranked_nodes=combined_ranked,
        selected_nodes=selected_nodes,
        filter_reasons=filter_reasons,
    )
    print("Quality reports:")
    print(json.dumps(report_paths, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    return _build_parser()


def main(argv: Optional[Iterable[str]] = None) -> int:
    return run(argv)


if __name__ == "__main__":
    raise SystemExit(run())
