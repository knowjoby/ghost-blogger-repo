from datetime import date
from pathlib import Path

from ghost_blogger.dedupe import fingerprint_for_run, fingerprint_marker, seen_fingerprint_today, seen_title_today
from ghost_blogger.dedupe import existing_urls_today


def test_seen_fingerprint_today(tmp_path: Path) -> None:
    day = date(2026, 3, 12)
    fp = fingerprint_for_run(day=day, source_urls=["https://example.com/a", "https://example.com/b"])
    assert not seen_fingerprint_today(tmp_path, day=day, fp=fp)

    f = tmp_path / f"{day:%Y-%m-%d}-x.md"
    f.write_text(f"{fingerprint_marker(fp)}\n\nbody\n", encoding="utf-8")
    assert seen_fingerprint_today(tmp_path, day=day, fp=fp)


def test_seen_title_today(tmp_path: Path) -> None:
    day = date(2026, 3, 12)
    assert not seen_title_today(tmp_path, day=day, title="Ghost notes: A")

    f = tmp_path / f"{day:%Y-%m-%d}-a.md"
    f.write_text("---\nlayout: post\ntitle: 'Ghost notes: A'\n---\n\nBody\n", encoding="utf-8")
    assert seen_title_today(tmp_path, day=day, title="Ghost notes: A")


def test_existing_urls_today(tmp_path: Path) -> None:
    day = date(2026, 3, 12)
    f = tmp_path / f"{day:%Y-%m-%d}-a.md"
    f.write_text(
        "---\nlayout: post\ntitle: 'T'\n---\n\nSource: [x](https://example.com/a)\n\nMore https://example.com/b.\n",
        encoding="utf-8",
    )
    urls = existing_urls_today(tmp_path, day=day)
    assert "https://example.com/a" in urls
    assert "https://example.com/b" in urls
