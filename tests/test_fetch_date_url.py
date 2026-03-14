import datetime

from fetch import Node, safe_strftime


def test_safe_strftime_handles_invalid_tokens():
    dt = datetime.datetime(2026, 3, 14, 12, 0, 0)
    template = "https://example.com/%Y/%m%/%n-%d.yaml"
    assert safe_strftime(dt, template) == "https://example.com/2026/03%/%n-14.yaml"


def test_safe_strftime_keeps_percent_encoded_segments():
    dt = datetime.datetime(2026, 3, 14, 12, 0, 0)
    template = "https://example.com/api/%2F/items/%Y%m%d.yaml"
    assert safe_strftime(dt, template) == "https://example.com/api/%2F/items/20260314.yaml"


def test_vless_query_value_can_contain_equals():
    node = Node(
        "vless://123e4567-e89b-12d3-a456-426614174000@example.com:443"
        "?type=ws&path=%2Ffoo%3Fbar%3Dbaz&pbk=abc==&sid=xyz"
        "#demo"
    )
    assert node.data["reality-opts"]["public-key"] == "abc=="
    assert node.data["reality-opts"]["short-id"] == "xyz"


def test_vless_query_item_without_equals_wont_crash():
    node = Node(
        "vless://123e4567-e89b-12d3-a456-426614174000@example.com:443"
        "?type=ws&flag&pbk=abc=="
        "#demo"
    )
    assert node.data["reality-opts"]["public-key"] == "abc=="


def test_format_name_accepts_non_string_name():
    node = Node(
        {
            "type": "ss",
            "name": 12345,
            "server": "127.0.0.1",
            "port": 443,
            "cipher": "aes-128-gcm",
            "password": "pass",
        }
    )
    node.format_name()
    assert isinstance(node.data["name"], str)


def test_isfake_handles_non_string_server():
    node = Node(
        {
            "type": "ss",
            "name": "test",
            "server": 12345,
            "port": 443,
            "cipher": "aes-128-gcm",
            "password": "pass",
        }
    )
    assert node.isfake is True


def test_vless_grpc_url_without_grpc_opts():
    node = Node(
        {
            "type": "vless",
            "name": 123,
            "server": "example.com",
            "port": 443,
            "uuid": "123e4567-e89b-12d3-a456-426614174000",
            "network": "grpc",
        }
    )
    assert "type=grpc" in node.url
