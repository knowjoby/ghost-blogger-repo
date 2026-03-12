from ghost_blogger.net import normalize_url, redact_pii_like


def test_normalize_url_strips_fragment() -> None:
    assert normalize_url("https://example.com/a#b") == "https://example.com/a"


def test_redact_pii_like() -> None:
    t = "email me at a.b+test@example.com or call 123-456-7890"
    r = redact_pii_like(t)
    assert "[redacted-email]" in r
    assert "[redacted-phone]" in r

