from fetch import resolve_public_snippet_categories


def test_resolve_public_snippet_categories_prefers_explicit_allowlist() -> None:
    snip_conf = {
        "snippet_categories": ["JP", "US", "GB", "SG", "TW", "HK"],
        "categories": {
            "JP": ["JP"],
            "US": ["US"],
            "GB": ["GB"],
            "SG": ["SG"],
            "TW": ["TW"],
            "HK": ["HK"],
            "DE": ["DE"],
        },
    }

    assert resolve_public_snippet_categories(snip_conf) == ["JP", "US", "GB", "SG", "TW", "HK"]


def test_resolve_public_snippet_categories_falls_back_to_all_categories() -> None:
    snip_conf = {
        "categories": {
            "JP": ["JP"],
            "US": ["US"],
            "DE": ["DE"],
        },
    }

    assert resolve_public_snippet_categories(snip_conf) == ["JP", "US", "DE"]
