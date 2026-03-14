import base64
import json

import pytest

from fetch import Node, UnsupportedType


def make_vmess_url(payload: dict) -> str:
    data = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return f"vmess://{data}"


def test_vmess_empty_alter_id_falls_back_to_zero() -> None:
    node = Node(
        make_vmess_url(
            {
                "v": "2",
                "ps": "demo",
                "add": "example.com",
                "port": "443",
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "aid": "",
                "net": "tcp",
                "scy": "auto",
            }
        )
    )

    assert node.data["alterId"] == 0


def test_vmess_invalid_alter_id_is_skipped_cleanly() -> None:
    with pytest.raises(UnsupportedType):
        Node(
            make_vmess_url(
                {
                    "v": "2",
                    "ps": "bad-aid",
                    "add": "example.com",
                    "port": "443",
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "aid": "\u0002",
                    "net": "tcp",
                    "scy": "auto",
                }
            )
        )


def test_ss_missing_port_is_skipped_cleanly() -> None:
    with pytest.raises(UnsupportedType):
        Node("ss://YWVzLTI1Ni1nY206cGFzcw@example.com#demo")


def test_ss_password_can_contain_colon() -> None:
    node = Node("ss://aes-256-gcm:pa:ss@example.com:443#demo")

    assert node.data["server"] == "example.com"
    assert node.data["port"] == 443
    assert node.data["password"] == "pa:ss"


def test_ss_invalid_base64_payload_is_skipped_cleanly() -> None:
    with pytest.raises(UnsupportedType):
        Node("ss:///w==@example.com:443#demo")


def test_ssr_invalid_base64_payload_is_skipped_cleanly() -> None:
    with pytest.raises(UnsupportedType):
        Node("ssr:///w==")


def test_trojan_trailing_space_port_is_parsed() -> None:
    node = Node("trojan://password@example.com:443 #demo")

    assert node.data["server"] == "example.com"
    assert node.data["port"] == 443


def test_vless_invalid_port_is_skipped_cleanly() -> None:
    with pytest.raises(UnsupportedType):
        Node("vless://123e4567-e89b-12d3-a456-426614174000@example.com:4 43#demo")


def test_hysteria2_default_port_remains_available() -> None:
    node = Node("hysteria2://password@example.com#demo")

    assert node.data["server"] == "example.com"
    assert node.data["port"] == 443


def test_hash_tolerates_null_ws_host() -> None:
    node = Node(
        {
            "type": "vmess",
            "name": "demo",
            "server": "example.com",
            "port": 443,
            "uuid": "123e4567-e89b-12d3-a456-426614174000",
            "alterId": 0,
            "cipher": "auto",
            "network": "ws",
            "ws-opts": {
                "headers": {"Host": None},
                "path": "/ws",
            },
        }
    )

    assert isinstance(hash(node), int)
