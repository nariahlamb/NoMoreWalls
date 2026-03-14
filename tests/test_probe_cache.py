from __future__ import annotations

from pathlib import Path

from quality.cache import CacheContext, ProbeCache
from quality.models import ProbeResult
from quality.probe_runner import parse_delay_response


def test_parse_delay_response_marks_success() -> None:
    result = parse_delay_response({"delay": 183})
    assert result.ok is True
    assert result.latency_ms == 183
    assert result.failure_reason == ""


def test_parse_delay_response_marks_failure() -> None:
    result = parse_delay_response({"message": "connect timeout"})
    assert result.ok is False
    assert result.failure_reason == "timeout"


def test_probe_cache_hit_and_context_bust(tmp_path: Path) -> None:
    cache = ProbeCache(
        cache_path=tmp_path / "probe_cache.json",
        session_state_path=tmp_path / "session_state.json",
        history_path=tmp_path / "probe_history.jsonl",
        ttl_seconds=60,
    )
    context_a = CacheContext(
        probe_urls=["https://a.example/204"],
        timeout_ms=5000,
        network_profile="net-a",
        mihomo_version="mihomo 1.19",
    ).key()
    context_b = CacheContext(
        probe_urls=["https://b.example/204"],
        timeout_ms=5000,
        network_profile="net-a",
        mihomo_version="mihomo 1.19",
    ).key()

    probe = ProbeResult(
        node_hash="node-1",
        ok=True,
        checked_at="2026-03-14T08:30:00Z",
        latency_ms=120,
        failure_reason="",
        details={},
    )
    cache.set("node-1", context_a, probe, now_ts=1000)

    hit = cache.get("node-1", context_a, now_ts=1001)
    assert hit is not None
    assert hit.ok is True
    assert hit.latency_ms == 120

    miss_context = cache.get("node-1", context_b, now_ts=1001)
    assert miss_context is None

    miss_ttl = cache.get("node-1", context_a, now_ts=1100)
    assert miss_ttl is None


def test_probe_cache_resume_state_round_trip(tmp_path: Path) -> None:
    cache = ProbeCache(
        cache_path=tmp_path / "probe_cache.json",
        session_state_path=tmp_path / "session_state.json",
        history_path=tmp_path / "probe_history.jsonl",
        ttl_seconds=60,
    )
    context_key = "ctx-1"
    pending = ["n1", "n2", "n3"]
    cache.save_resume_state(context_key, pending)

    loaded = cache.load_resume_state(context_key, ["n1", "n2", "n4"])
    assert loaded == ["n1", "n2"]

    cache.clear_resume_state()
    assert cache.load_resume_state(context_key, ["n1"]) == ["n1"]
