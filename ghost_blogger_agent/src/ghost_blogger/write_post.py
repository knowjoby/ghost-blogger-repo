from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Union

import yaml


@dataclass(frozen=True)
class Post:
    title: str
    date: datetime
    tags: list[str]
    body_md: str


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(title: str, *, max_len: int = 80) -> str:
    t = title.strip().lower()
    t = _SLUG_RE.sub("-", t).strip("-")
    if not t:
        return "post"
    return t[:max_len].strip("-")


def render_jekyll_markdown(post: Post) -> str:
    front_matter = {
        "layout": "post",
        "title": post.title,
        "date": post.date.isoformat(timespec="minutes"),
        "tags": post.tags,
    }
    fm = yaml.safe_dump(front_matter, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm}\n---\n\n{post.body_md.strip()}\n"


def write_new_post(posts_dir: Union[str, Path], post: Post) -> Path:
    out_dir = Path(posts_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = slugify(post.title)
    base = f"{post.date:%Y-%m-%d}-{slug}.md"
    candidate = out_dir / base
    i = 1
    while candidate.exists():
        candidate = out_dir / f"{post.date:%Y-%m-%d}-{slug}-{i}.md"
        i += 1

    candidate.write_text(render_jekyll_markdown(post), encoding="utf-8")
    return candidate
