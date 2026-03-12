from ghost_blogger.validation import validate_post_markdown


def test_validation_happy_path() -> None:
    md = (
        "## TL;DR\n\n- A\n\n"
        "## What I read\n\n- [A](https://example.com)\n\n"
        "## What I learned\n\n### A\n\n"
        "Something with enough detail to pass a minimal length check. "
        "Another sentence to ensure this looks like a real note.\n\n"
        "Source: [https://example.com](https://example.com)\n\n"
        "## My take (reflective voice)\n\nI am not sentient.\n"
    )
    assert validate_post_markdown(md, notes_count=1) == []


def test_validation_requires_disclaimer() -> None:
    md = (
        "## TL;DR\n\n- A\n\n"
        "## What I read\n\n- [A](https://example.com)\n\n"
        "## What I learned\n\n### A\n\nSomething.\n\nSource: [https://example.com](https://example.com)\n\n"
        "## My take (reflective voice)\n\nReflection.\n"
    )
    errs = validate_post_markdown(md, notes_count=1)
    assert any("not sentient" in e for e in errs)
