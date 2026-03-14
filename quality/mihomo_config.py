from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import yaml

from quality.models import RankedNode


def _normalize_proxy_payload(snapshot_payload: Mapping[str, Any], fallback_name: str) -> Dict[str, Any]:
    payload = dict(snapshot_payload)
    payload["name"] = str(payload.get("name") or fallback_name)
    payload["type"] = str(payload.get("type") or payload.get("protocol") or "")
    return payload


def load_probe_template(template_path: str) -> Dict[str, Any]:
    path = Path(template_path)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if isinstance(loaded, dict):
        return loaded
    return {}


def build_probe_config(
    candidates: Sequence[RankedNode],
    probe_settings: Mapping[str, Any],
    template_path: str = "snippets/example.yml",
) -> Dict[str, Any]:
    template = load_probe_template(template_path)
    config = {
        "allow-lan": False,
        "external-controller": "127.0.0.1:19090",
        "mode": "rule",
        "log-level": "warning",
        "dns": deepcopy(template.get("dns") or {}),
        "proxies": [],
        "proxy-groups": [],
        "rules": ["MATCH,QUALITY-PROBE-SELECT"],
    }

    controller_host = str(probe_settings.get("controller_host", "127.0.0.1"))
    controller_port = int(probe_settings.get("controller_port", 19090))
    test_url = str(
        (probe_settings.get("urls") or probe_settings.get("targets") or ["https://www.gstatic.com/generate_204"])[0]
    )
    test_interval = int(probe_settings.get("test_interval_s", 300))

    proxies: List[Dict[str, Any]] = []
    proxy_names: List[str] = []
    for item in candidates:
        proxy_payload = _normalize_proxy_payload(item.snapshot.payload, item.snapshot.name)
        if not proxy_payload.get("name"):
            continue
        proxies.append(proxy_payload)
        proxy_names.append(str(proxy_payload["name"]))

    config["external-controller"] = f"{controller_host}:{controller_port}"
    config["proxies"] = proxies
    config["proxy-groups"] = [
        {
            "name": "QUALITY-PROBE",
            "type": "url-test",
            "url": test_url,
            "interval": test_interval,
            "proxies": proxy_names,
        },
        {
            "name": "QUALITY-PROBE-SELECT",
            "type": "select",
            "proxies": ["QUALITY-PROBE"] + proxy_names,
        },
    ]

    if config["dns"] and "enable" not in config["dns"]:
        config["dns"]["enable"] = True
    return config


def write_probe_config(path: Path, config: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.dump(dict(config), handle, allow_unicode=True, sort_keys=False)
    return path
