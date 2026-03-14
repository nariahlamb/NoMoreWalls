from __future__ import annotations

import hashlib
import json
import os
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from quality.models import ProbeResult


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _json_hash(payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_network_profile() -> str:
    profile = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "http_proxy": os.environ.get("HTTP_PROXY", ""),
        "https_proxy": os.environ.get("HTTPS_PROXY", ""),
    }
    return _json_hash(profile)


@dataclass(frozen=True)
class CacheContext:
    probe_urls: List[str]
    timeout_ms: int
    network_profile: str
    mihomo_version: str

    def key(self) -> str:
        return _json_hash(
            {
                "probe_urls": sorted(self.probe_urls),
                "timeout_ms": self.timeout_ms,
                "network_profile": self.network_profile,
                "mihomo_version": self.mihomo_version,
            }
        )


class ProbeCache:
    def __init__(
        self,
        cache_path: Path,
        session_state_path: Path,
        history_path: Path,
        ttl_seconds: int = 21600,
    ) -> None:
        self.cache_path = cache_path
        self.session_state_path = session_state_path
        self.history_path = history_path
        self.ttl_seconds = int(ttl_seconds)

    def clear(self) -> None:
        for path in (self.cache_path, self.session_state_path):
            if path.exists():
                path.unlink()

    def _load_json(self, path: Path, default: Mapping[str, Any]) -> Dict[str, Any]:
        if not path.exists():
            return dict(default)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return dict(default)

    def _save_json(self, path: Path, payload: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def get(self, node_hash: str, context_key: str, now_ts: Optional[float] = None) -> Optional[ProbeResult]:
        now_ts = float(now_ts or datetime.now(timezone.utc).timestamp())
        cache_data = self._load_json(self.cache_path, {"entries": {}})
        item = (cache_data.get("entries") or {}).get(node_hash)
        if not item:
            return None
        if item.get("context_key") != context_key:
            return None
        updated_at = float(item.get("updated_at", 0))
        if self.ttl_seconds > 0 and now_ts - updated_at > self.ttl_seconds:
            return None
        result = item.get("result")
        if not isinstance(result, Mapping):
            return None
        return ProbeResult.from_dict(result)

    def set(self, node_hash: str, context_key: str, result: ProbeResult, now_ts: Optional[float] = None) -> None:
        now_ts = float(now_ts or datetime.now(timezone.utc).timestamp())
        cache_data = self._load_json(self.cache_path, {"entries": {}})
        entries = dict(cache_data.get("entries") or {})
        entries[node_hash] = {
            "context_key": context_key,
            "updated_at": now_ts,
            "result": result.to_dict(),
        }
        cache_data["entries"] = entries
        cache_data["schema_version"] = 1
        self._save_json(self.cache_path, cache_data)

    def append_history(self, context_key: str, result: ProbeResult) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "context_key": context_key,
            "recorded_at": _utc_now_iso(),
            "result": result.to_dict(),
        }
        with self.history_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    def load_resume_state(self, context_key: str, node_hashes: Sequence[str]) -> List[str]:
        state = self._load_json(self.session_state_path, {"context_key": "", "pending": []})
        if state.get("context_key") != context_key:
            return list(node_hashes)
        pending = [str(item) for item in state.get("pending") or []]
        pending_set = set(pending)
        # Drop stale items and keep deterministic order.
        return [node_hash for node_hash in node_hashes if node_hash in pending_set]

    def save_resume_state(self, context_key: str, pending: Iterable[str]) -> None:
        payload = {
            "schema_version": 1,
            "context_key": context_key,
            "updated_at": _utc_now_iso(),
            "pending": [str(item) for item in pending],
        }
        self._save_json(self.session_state_path, payload)

    def clear_resume_state(self) -> None:
        if self.session_state_path.exists():
            self.session_state_path.unlink()
