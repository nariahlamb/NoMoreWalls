from __future__ import annotations

import json
from pathlib import Path

from optimize_local import build_parser, main
from quality.mihomo_config import build_probe_config
from quality.passive_score import rank_nodes_passively


def test_cli_supports_required_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--full-probe",
            "--mihomo-path",
            "/usr/bin/mihomo",
            "--reuse-cache",
            "--clear-cache",
            "--snapshot-path",
            "artifacts/quality/node_snapshot.jsonl",
        ]
    )
    assert args.full_probe is True
    assert args.mihomo_path == "/usr/bin/mihomo"
    assert args.reuse_cache is True
    assert args.clear_cache is True


def test_build_probe_config_includes_shortlisted_candidates(
    sample_snapshot_records,
    local_quality_config,
) -> None:
    ranked = rank_nodes_passively(sample_snapshot_records, config=local_quality_config)
    config = build_probe_config(
        ranked[:2],
        {
            "controller_host": "127.0.0.1",
            "controller_port": 19090,
            "targets": ["https://www.google.com/generate_204"],
        },
    )
    assert config["proxies"]
    assert any(group["name"] == "QUALITY-PROBE" for group in config["proxy-groups"])
    assert config["external-controller"] == "127.0.0.1:19090"


def test_cli_report_only_uses_existing_artifacts(
    tmp_path: Path,
    sample_snapshot_records,
    sample_snapshot_path: Path,
    local_quality_config,
) -> None:
    artifacts_dir = tmp_path / "artifacts"
    quality_dir = artifacts_dir / "quality"
    quality_dir.mkdir(parents=True, exist_ok=True)

    ranked = rank_nodes_passively(sample_snapshot_records, config=local_quality_config)
    (quality_dir / "ranked_nodes.json").write_text(
        json.dumps([item.to_dict() for item in ranked[:2]], ensure_ascii=False),
        encoding="utf-8",
    )
    (quality_dir / "filter_reasons.json").write_text(
        json.dumps([{"node_hash": "dummy", "name": "dummy", "reason_code": "x", "reason": "x"}], ensure_ascii=False),
        encoding="utf-8",
    )
    snapshot_path = quality_dir / "node_snapshot.jsonl"
    snapshot_path.write_text(sample_snapshot_path.read_text(encoding="utf-8"), encoding="utf-8")
    config_path = tmp_path / "local_quality.yml"
    config_path.write_text("{}", encoding="utf-8")

    exit_code = main(
        [
            "--report-only",
            "--artifacts-dir",
            str(artifacts_dir),
            "--snapshot-path",
            str(snapshot_path),
            "--quality-config",
            str(config_path),
        ]
    )
    assert exit_code == 0
    assert (quality_dir / "summary.md").exists()


def test_cli_passive_only_generates_local_outputs(
    tmp_path: Path,
    sample_snapshot_path: Path,
) -> None:
    artifacts_dir = tmp_path / "artifacts"
    quality_dir = artifacts_dir / "quality"
    quality_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = quality_dir / "node_snapshot.jsonl"
    snapshot_path.write_text(sample_snapshot_path.read_text(encoding="utf-8"), encoding="utf-8")

    config_path = tmp_path / "local_quality.yml"
    config_path.write_text("{}", encoding="utf-8")

    exit_code = main(
        [
            "--passive-only",
            "--snapshot-path",
            str(snapshot_path),
            "--artifacts-dir",
            str(artifacts_dir),
            "--quality-config",
            str(config_path),
        ]
    )
    assert exit_code == 0
    assert (artifacts_dir / "local" / "list.local.txt").exists()
    assert (artifacts_dir / "quality" / "summary.md").exists()
