from __future__ import annotations

from quality.passive_score import infer_categories, rank_nodes_passively, score_snapshot


def test_multi_source_hysteria2_scores_higher_than_single_source_ss(
    sample_snapshot_records,
    local_quality_config,
) -> None:
    strong = score_snapshot(sample_snapshot_records[0], config=local_quality_config)
    weak = score_snapshot(sample_snapshot_records[1], config=local_quality_config)
    assert strong.total > weak.total
    assert strong.breakdown["protocol"] > weak.breakdown["protocol"]
    assert strong.breakdown["provenance"] > weak.breakdown["provenance"]


def test_fake_metadata_penalty_is_explained(sample_snapshot_records, local_quality_config) -> None:
    weak = score_snapshot(sample_snapshot_records[1], config=local_quality_config)
    assert weak.breakdown["fake_risk_penalty"] < 0
    assert weak.breakdown["duplicate_conflict_penalty"] < 0
    assert "suspicious_endpoint" in weak.flags
    assert any(flag.startswith("keyword:free") for flag in weak.flags)


def test_repo_category_keywords_contribute_to_category_confidence(
    sample_snapshot_records,
    local_quality_config,
) -> None:
    categories = infer_categories(sample_snapshot_records[2], config=local_quality_config)
    score = score_snapshot(sample_snapshot_records[2], config=local_quality_config)
    assert "US" in categories
    assert "US" in score.matched_categories
    assert score.breakdown["category_confidence"] > 0


def test_rank_nodes_passively_orders_by_total_score(sample_snapshot_records, local_quality_config) -> None:
    ranked = rank_nodes_passively(sample_snapshot_records, config=local_quality_config)
    assert [item.snapshot.protocol for item in ranked[:2]] == ["hysteria2", "vless"]
    assert ranked[0].final_score >= ranked[1].final_score >= ranked[2].final_score
    assert ranked[0].rank == 1
