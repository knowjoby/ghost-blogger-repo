from datetime import date
from pathlib import Path

from ghost_blogger.dedupe import fingerprint_for_run, fingerprint_marker, seen_fingerprint_today


def test_seen_fingerprint_today(tmp_path: Path) -> None:
    day = date(2026, 3, 12)
    fp = fingerprint_for_run(day=day, source_urls=["https://example.com/a", "https://example.com/b"])
    assert not seen_fingerprint_today(tmp_path, day=day, fp=fp)

    f = tmp_path / f"{day:%Y-%m-%d}-x.md"
    f.write_text(f"{fingerprint_marker(fp)}\n\nbody\n", encoding="utf-8")
    assert seen_fingerprint_today(tmp_path, day=day, fp=fp)

