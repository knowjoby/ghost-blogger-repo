from ghost_blogger.extract import extract_readable_text


def test_extract_strips_scripts() -> None:
    html = "<html><head><title>T</title><script>bad()</script></head><body><main>Hello</main></body></html>"
    ex = extract_readable_text(html)
    assert ex.title == "T"
    assert "bad" not in ex.text
    assert "Hello" in ex.text

