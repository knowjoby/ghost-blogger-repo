from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path
from typing import Iterable


def fingerprint_for_run(*, day: date, source_urls: Iterable[str]) -> str:
    urls = sorted({u.strip() for u in source_urls if u and u.strip()})
    base = f"{day.isoformat()}\n" + "\n".join(urls)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def fingerprint_marker(fp: str) -> str:
    return f"<!-- ghost:fingerprint:{fp} -->"


def seen_fingerprint_today(posts_dir: str | Path, *, day: date, fp: str) -> bool:
    pdir = Path(posts_dir)
    if not pdir.exists():
        return False

    marker = fingerprint_marker(fp)
    prefix = f"{day:%Y-%m-%d}-"
    for f in pdir.glob(f"{prefix}*.md"):
        try:
            if marker in f.read_text(encoding="utf-8", errors="ignore"):
                return True
        except OSError:
            continue
    return False

