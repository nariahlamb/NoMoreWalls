from __future__ import annotations

from pathlib import Path

import yaml

from quality.output_writer import write_local_outputs
from quality.passive_score import rank_nodes_passively


def test_write_local_outputs_keeps_root_outputs_untouched(
    tmp_path: Path,
    sample_snapshot_records,
    local_quality_config,
) -> None:
    ranked = rank_nodes_passively(sample_snapshot_records, config=local_quality_config)
    outputs = write_local_outputs(
        artifacts_dir=tmp_path / "artifacts",
        ranked_nodes=ranked,
        probe_url="https://www.gstatic.com/generate_204",
    )

    assert outputs.list_local_meta_yml.exists()
    assert outputs.nodes_local_yml.exists()
    assert outputs.nodes_local_meta_yml.exists()

    assert not (tmp_path / "list.txt").exists()
    assert not (tmp_path / "list.yml").exists()

    nodes_yaml = yaml.safe_load(outputs.nodes_local_yml.read_text(encoding="utf-8"))
    assert isinstance(nodes_yaml.get("proxies"), list)
    assert len(nodes_yaml["proxies"]) == len(ranked)
