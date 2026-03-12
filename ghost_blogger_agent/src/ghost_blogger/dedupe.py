from __future__ import annotations

import hashlib
import re
from datetime import date
from pathlib import Path
from typing import Iterable, Optional


_URL_RE = re.compile(r"https?://[^\s)>\"]+")


def fingerprint_for_run(*, day: date, source_urls: Iterable[str]) -> str:
    urls = sorted({u.strip() for u in source_urls if u and u.strip()})
    base = f"{day.isoformat()}\n" + "\n".join(urls)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def fingerprint_marker(fp: str) -> str:
    return f"<!-- ghost:fingerprint:{fp} -->"

def _extract_front_matter_title(text: str) -> Optional[str]:
    if not text.startswith("---"):
        return None
    # Very small YAML subset parsing: look for a single-line `title:` in the first block.
    lines = text.splitlines()
    if len(lines) < 3:
        return None
    # Find end of front matter
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        end = min(len(lines), 60)
    for ln in lines[1:end]:
        if ln.lower().startswith("title:"):
            v = ln.split(":", 1)[1].strip()
            if (v.startswith("'") and v.endswith("'")) or (v.startswith('"') and v.endswith('"')):
                v = v[1:-1].strip()
            return v or None
    return None


def seen_title_today(posts_dir: str | Path, *, day: date, title: str) -> bool:
    pdir = Path(posts_dir)
    if not pdir.exists():
        return False
    t = (title or "").strip().casefold()
    if not t:
        return False
    prefix = f"{day:%Y-%m-%d}-"
    for f in pdir.glob(f"{prefix}*.md"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        ft = _extract_front_matter_title(content)
        if ft and ft.strip().casefold() == t:
            return True
    return False


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


def existing_urls_today(posts_dir: str | Path, *, day: date) -> set[str]:
    pdir = Path(posts_dir)
    if not pdir.exists():
        return set()
    prefix = f"{day:%Y-%m-%d}-"
    urls: set[str] = set()
    for f in pdir.glob(f"{prefix}*.md"):
        try:
            # Only scan the first part; URLs appear early in our template.
            content = f.read_text(encoding="utf-8", errors="ignore")[:25_000]
        except OSError:
            continue
        for u in _URL_RE.findall(content):
            urls.add(u.rstrip(").,]"))
    return urls
