from datetime import datetime, timezone

from ghost_blogger.write_post import Post, render_jekyll_markdown, slugify


def test_slugify_basic() -> None:
    assert slugify("Hello, World!") == "hello-world"
    assert slugify("   ") == "post"


def test_render_has_front_matter() -> None:
    post = Post(
        title="Test",
        date=datetime(2026, 3, 12, 12, 0, tzinfo=timezone.utc),
        tags=["a", "b"],
        body_md="Body",
    )
    md = render_jekyll_markdown(post)
    assert md.startswith("---\n")
    assert "\nlayout: post\n" in md
    assert "\n---\n\nBody\n" in md

