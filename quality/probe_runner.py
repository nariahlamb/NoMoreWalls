from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence
from urllib.parse import quote

import requests

from quality.cache import CacheContext, ProbeCache, build_network_profile
from quality.mihomo_config import build_probe_config, write_probe_config
from quality.models import ProbeResult, RankedNode


@dataclass(frozen=True)
class DelayParseResult:
    ok: bool
    latency_ms: Optional[float]
    failure_reason: str
    details: Dict[str, Any]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def classify_probe_failure(
    message: str = "",
    *,
    status_code: Optional[int] = None,
    error: Optional[BaseException] = None,
) -> str:
    text = (message or "").lower()
    if error is not None:
        text = f"{text} {error}".lower()

    if status_code in (401, 403) or "auth" in text:
        return "auth_failed"
    if "tls" in text or "certificate" in text or "x509" in text:
        return "tls_failed"
    if "timeout" in text or "deadline" in text:
        return "timeout"
    if "connect" in text or "refused" in text or "unreachable" in text:
        return "connect_failed"
    if status_code is not None and status_code >= 500:
        return "connect_failed"
    return "empty_result"


def parse_delay_response(payload: Mapping[str, Any]) -> DelayParseResult:
    delay = payload.get("delay")
    if isinstance(delay, (int, float)) and delay >= 0:
        return DelayParseResult(ok=True, latency_ms=float(delay), failure_reason="", details=dict(payload))

    message = str(payload.get("message") or payload.get("error") or "")
    reason = classify_probe_failure(message=message)
    return DelayParseResult(ok=False, latency_ms=None, failure_reason=reason, details=dict(payload))


def build_mihomo_command(mihomo_path: str, config_path: Path) -> List[str]:
    return [mihomo_path, "-f", str(config_path)]


def resolve_mihomo_path(cli_path: Optional[str], probe_settings: Mapping[str, Any]) -> Optional[str]:
    for candidate in (
        cli_path,
        str(probe_settings.get("mihomo_path", "") or ""),
        os.environ.get("MIHOMO_PATH", ""),
        shutil.which("mihomo") or "",
        shutil.which("clash-meta") or "",
    ):
        if not candidate:
            continue
        if Path(candidate).exists():
            return str(Path(candidate))
        found = shutil.which(candidate)
        if found:
            return found
    return None


def _probe_one_proxy(base_url: str, proxy_name: str, probe_urls: Sequence[str], timeout_ms: int) -> ProbeResult:
    endpoint = f"{base_url}/proxies/{quote(proxy_name, safe='')}/delay"
    errors: List[str] = []
    delays: List[float] = []

    for target_url in probe_urls:
        try:
            response = requests.get(
                endpoint,
                params={"url": target_url, "timeout": timeout_ms},
                timeout=(3.0, (timeout_ms / 1000.0) + 3.0),
            )
            payload = response.json() if response.content else {}
            if response.status_code != 200:
                errors.append(classify_probe_failure(message=str(payload), status_code=response.status_code))
                continue
            parsed = parse_delay_response(payload)
            if parsed.ok and parsed.latency_ms is not None:
                delays.append(parsed.latency_ms)
            else:
                errors.append(parsed.failure_reason)
        except requests.Timeout as exc:
            errors.append(classify_probe_failure(message="timeout", error=exc))
        except requests.RequestException as exc:
            errors.append(classify_probe_failure(message="connect", error=exc))
        except ValueError as exc:
            errors.append(classify_probe_failure(message="invalid-json", error=exc))

    if delays:
        return ProbeResult(
            node_hash="",
            ok=True,
            checked_at=_utc_now_iso(),
            latency_ms=min(delays),
            failure_reason="",
            details={"sample_count": len(delays), "url_count": len(probe_urls)},
        )

    reason = errors[0] if errors else "empty_result"
    return ProbeResult(
        node_hash="",
        ok=False,
        checked_at=_utc_now_iso(),
        latency_ms=None,
        failure_reason=reason,
        details={"errors": errors},
    )


def _wait_controller_ready(base_url: str, startup_timeout_s: int, interval_s: float) -> bool:
    deadline = time.time() + max(1, startup_timeout_s)
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/version", timeout=2.0)
            if response.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(max(interval_s, 0.1))
    return False


def _read_mihomo_version(mihomo_path: str) -> str:
    try:
        completed = subprocess.run(
            [mihomo_path, "-v"],
            check=False,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except Exception:
        return "unknown"
    output = (completed.stdout or completed.stderr or "").strip().splitlines()
    return output[0] if output else "unknown"


def run_active_probe(
    candidates: Sequence[RankedNode],
    probe_settings: Mapping[str, Any],
    template_path: str,
    *,
    mihomo_path: Optional[str] = None,
    cache: Optional[ProbeCache] = None,
    reuse_cache: bool = False,
    clear_cache: bool = False,
    network_profile: Optional[str] = None,
) -> Dict[str, ProbeResult]:
    if not candidates:
        return {}

    resolved_mihomo = resolve_mihomo_path(mihomo_path, probe_settings)
    if not resolved_mihomo:
        raise FileNotFoundError("mihomo binary not found")

    probe_urls = [str(item) for item in (probe_settings.get("urls") or []) if str(item)]
    if not probe_urls:
        probe_urls = ["https://www.gstatic.com/generate_204"]
    timeout_ms = int(probe_settings.get("timeout_ms", 5000))
    startup_timeout_s = int(probe_settings.get("startup_timeout_s", 20))
    healthcheck_interval_s = float(probe_settings.get("healthcheck_interval_s", 0.5))
    controller_host = str(probe_settings.get("controller_host", "127.0.0.1"))
    controller_port = int(probe_settings.get("controller_port", 19090))
    max_candidates = int(probe_settings.get("max_candidates", len(candidates)))

    run_candidates = list(candidates)[:max_candidates]
    profile = network_profile or build_network_profile()
    context = CacheContext(
        probe_urls=probe_urls,
        timeout_ms=timeout_ms,
        network_profile=profile,
        mihomo_version=_read_mihomo_version(resolved_mihomo),
    )
    context_key = context.key()

    if cache and clear_cache:
        cache.clear()

    results: Dict[str, ProbeResult] = {}
    pending: List[RankedNode] = []
    for node in run_candidates:
        cached_result = cache.get(node.snapshot.node_hash, context_key) if cache and reuse_cache else None
        if cached_result:
            results[node.snapshot.node_hash] = cached_result
            continue
        pending.append(node)

    if cache and reuse_cache and pending:
        ordered_hashes = [node.snapshot.node_hash for node in pending]
        resume_hashes = set(cache.load_resume_state(context_key, ordered_hashes))
        if resume_hashes:
            pending = [node for node in pending if node.snapshot.node_hash in resume_hashes]

    if not pending:
        return results

    base_url = f"http://{controller_host}:{controller_port}"
    if cache:
        cache.save_resume_state(context_key, [node.snapshot.node_hash for node in pending])

    with tempfile.TemporaryDirectory(prefix="local-quality-probe-") as temp_dir:
        temp_path = Path(temp_dir)
        config_path = write_probe_config(
            temp_path / "mihomo-probe.yml",
            build_probe_config(pending, probe_settings, template_path=template_path),
        )

        process = subprocess.Popen(
            build_mihomo_command(resolved_mihomo, config_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            ready = _wait_controller_ready(base_url, startup_timeout_s=startup_timeout_s, interval_s=healthcheck_interval_s)
            if not ready:
                for node in pending:
                    result = ProbeResult(
                        node_hash=node.snapshot.node_hash,
                        ok=False,
                        checked_at=_utc_now_iso(),
                        latency_ms=None,
                        failure_reason="connect_failed",
                        details={"message": "controller_not_ready"},
                    )
                    results[node.snapshot.node_hash] = result
                    if cache:
                        cache.set(node.snapshot.node_hash, context_key, result)
                        cache.append_history(context_key, result)
                return results

            remaining = [node.snapshot.node_hash for node in pending]
            for node in pending:
                probe_result = _probe_one_proxy(
                    base_url=base_url,
                    proxy_name=node.snapshot.name,
                    probe_urls=probe_urls,
                    timeout_ms=timeout_ms,
                )
                probe_result = ProbeResult(
                    node_hash=node.snapshot.node_hash,
                    ok=probe_result.ok,
                    checked_at=probe_result.checked_at,
                    latency_ms=probe_result.latency_ms,
                    failure_reason=probe_result.failure_reason,
                    details=probe_result.details,
                )
                results[node.snapshot.node_hash] = probe_result

                if cache:
                    cache.set(node.snapshot.node_hash, context_key, probe_result)
                    cache.append_history(context_key, probe_result)
                    remaining = [item for item in remaining if item != node.snapshot.node_hash]
                    cache.save_resume_state(context_key, remaining)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            if cache:
                cache.clear_resume_state()

    return results
