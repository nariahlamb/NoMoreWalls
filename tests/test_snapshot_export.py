from __future__ import annotations

from types import SimpleNamespace

from fetch import Node
from quality.models import NodeSnapshot, compute_node_hash, load_snapshot_jsonl
from quality.provenance import export_quality_artifacts


def test_snapshot_record_has_required_fields(sample_snapshot_record: NodeSnapshot) -> None:
    assert sample_snapshot_record.node_hash
    assert sample_snapshot_record.protocol in {"vmess", "vless", "trojan", "ss", "ssr", "hysteria2"}
    assert isinstance(sample_snapshot_record.source_ids, list)
    assert sample_snapshot_record.port > 0
    assert sample_snapshot_record.merged_at


def test_snapshot_hash_is_stable_for_same_identity_payload(sample_snapshot_record: NodeSnapshot) -> None:
    payload = dict(sample_snapshot_record.payload)
    hash_a = compute_node_hash(
        protocol=sample_snapshot_record.protocol,
        server=sample_snapshot_record.server,
        port=sample_snapshot_record.port,
        payload=payload,
    )
    payload["ignored_field"] = "noise"
    hash_b = compute_node_hash(
        protocol=sample_snapshot_record.protocol,
        server=sample_snapshot_record.server,
        port=sample_snapshot_record.port,
        payload=payload,
    )
    assert hash_a == hash_b == sample_snapshot_record.node_hash


def test_snapshot_json_round_trip_preserves_contract(sample_snapshot_record: NodeSnapshot) -> None:
    restored = NodeSnapshot.from_json_line(sample_snapshot_record.to_json_line())
    assert restored.to_dict() == sample_snapshot_record.to_dict()
    assert restored.provenance[0].source_id == sample_snapshot_record.source_ids[0]


def test_snapshot_fixture_contains_realistic_source_provenance(sample_snapshot_records: list[NodeSnapshot]) -> None:
    assert len(sample_snapshot_records) == 3
    assert sample_snapshot_records[0].source_count == 2
    assert sample_snapshot_records[1].provenance[0].raw_name == sample_snapshot_records[1].raw_name


def test_fetch_exports_quality_snapshot(tmp_path) -> None:
    node_a = Node(
        {
            "name": "HK VMESS",
            "type": "vmess",
            "server": "hk-1.example.com",
            "port": 443,
            "uuid": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "alterId": 0,
            "cipher": "auto",
            "network": "tcp",
            "tls": True,
        }
    )
    node_b = Node(
        {
            "name": "US SS",
            "type": "ss",
            "server": "us-1.example.com",
            "port": 8388,
            "cipher": "aes-256-gcm",
            "password": "pw",
        }
    )

    merged = {hash(node_a): node_a, hash(node_b): node_b}
    used = {
        hash(node_a): {0: "raw-hk-vmess", 1: "raw-hk-vmess-mirror"},
        hash(node_b): {1: "raw-us-ss"},
    }
    unknown = {"unknown://bad-node"}
    sources = [
        SimpleNamespace(url="https://source-a.example/sub", sub=["a", "b"]),
        SimpleNamespace(url="https://source-b.example/sub", sub=["c"]),
    ]

    output_dir = tmp_path / "quality"
    paths = export_quality_artifacts(
        merged_nodes=merged,
        used_map=used,
        unknown_nodes=unknown,
        sources=sources,
        output_dir=str(output_dir),
    )

    assert (output_dir / "node_snapshot.jsonl").exists()
    assert (output_dir / "source_summary.csv").exists()
    assert (output_dir / "merge_stats.json").exists()
    assert (output_dir / "unknown_nodes.txt").exists()

    assert paths["snapshot"].endswith("node_snapshot.jsonl")

    snapshots = load_snapshot_jsonl((output_dir / "node_snapshot.jsonl").read_text(encoding="utf-8").splitlines())
    assert len(snapshots) == 2
    assert all(item.node_hash for item in snapshots)
    assert sorted(snapshots[0].source_ids + snapshots[1].source_ids)
