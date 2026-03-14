from __future__ import annotations

import base64
import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence
from urllib.parse import quote

import yaml

from quality.models import RankedNode


@dataclass(frozen=True)
class LocalOutputPaths:
    list_local_txt: Path
    list_local_yml: Path
    list_local_meta_yml: Path
    nodes_local_yml: Path
    nodes_local_meta_yml: Path

    def as_dict(self) -> Dict[str, str]:
        return {
            "list_local_txt": str(self.list_local_txt),
            "list_local_yml": str(self.list_local_yml),
            "list_local_meta_yml": str(self.list_local_meta_yml),
            "nodes_local_yml": str(self.nodes_local_yml),
            "nodes_local_meta_yml": str(self.nodes_local_meta_yml),
        }


def _b64_encode(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("utf-8")


def _node_payloads(ranked_nodes: Sequence[RankedNode]) -> list[Dict[str, Any]]:
    proxies: list[Dict[str, Any]] = []
    for item in ranked_nodes:
        payload = dict(item.snapshot.payload)
        payload["name"] = item.snapshot.name
        payload["type"] = item.snapshot.protocol
        proxies.append(payload)
    return proxies


def _build_local_clash_config(proxies: Sequence[Mapping[str, Any]], probe_url: str) -> Dict[str, Any]:
    names = [str(proxy.get("name", "")) for proxy in proxies if str(proxy.get("name", ""))]
    return {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "warning",
        "proxies": list(proxies),
        "proxy-groups": [
            {
                "name": "LOCAL-AUTO",
                "type": "url-test",
                "url": probe_url,
                "interval": 300,
                "proxies": names,
            },
            {
                "name": "LOCAL-SELECT",
                "type": "select",
                "proxies": ["LOCAL-AUTO"] + names,
            },
        ],
        "rules": ["MATCH,LOCAL-SELECT"],
    }


def _render_v2ray_lines(proxies: Sequence[Mapping[str, Any]]) -> str:
    lines: list[str] = []
    for payload in proxies:
        protocol = str(payload.get("type", "")).strip().lower()
        server = str(payload.get("server", "")).strip()
        port = payload.get("port")
        name = quote(str(payload.get("name", "NoName")))
        try:
            port_int = int(port)
        except (TypeError, ValueError):
            continue
        if not protocol or not server or port_int <= 0:
            continue
        lines.append(f"{protocol}://{server}:{port_int}#{name}")
    return "\n".join(lines) + ("\n" if lines else "")


def _write_yaml_with_header(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    header = datetime.datetime.now().strftime("# Update: %Y-%m-%d %H:%M\n")
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(header)
        handle.write(yaml.dump(dict(payload), allow_unicode=True, sort_keys=False).replace("!!str ", ""))


def write_local_outputs(
    artifacts_dir: Path,
    ranked_nodes: Sequence[RankedNode],
    probe_url: str,
) -> LocalOutputPaths:
    local_dir = artifacts_dir / "local"
    snippets_dir = local_dir / "snippets"
    snippets_dir.mkdir(parents=True, exist_ok=True)

    proxies = _node_payloads(ranked_nodes)
    clash_conf = _build_local_clash_config(proxies, probe_url=probe_url)

    list_local_txt = local_dir / "list.local.txt"
    list_local_yml = local_dir / "list.local.yml"
    list_local_meta_yml = local_dir / "list.local.meta.yml"
    nodes_local_yml = snippets_dir / "nodes.local.yml"
    nodes_local_meta_yml = snippets_dir / "nodes.local.meta.yml"

    raw_v2ray = _render_v2ray_lines(proxies)
    list_local_txt.parent.mkdir(parents=True, exist_ok=True)
    list_local_txt.write_text(_b64_encode(raw_v2ray), encoding="utf-8", newline="\n")

    _write_yaml_with_header(list_local_yml, clash_conf)
    _write_yaml_with_header(list_local_meta_yml, clash_conf)

    with nodes_local_yml.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.dump({"proxies": proxies}, handle, allow_unicode=True, sort_keys=False)
    with nodes_local_meta_yml.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.dump({"proxies": proxies}, handle, allow_unicode=True, sort_keys=False)

    return LocalOutputPaths(
        list_local_txt=list_local_txt,
        list_local_yml=list_local_yml,
        list_local_meta_yml=list_local_meta_yml,
        nodes_local_yml=nodes_local_yml,
        nodes_local_meta_yml=nodes_local_meta_yml,
    )
