from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

from ghost_blogger.write_post import Post, write_new_post


def _data_dir(config_path: str) -> Path:
    cfg_path = Path(config_path).resolve()
    cfg = yaml.safe_load(cfg_path.read_text())
    posts_dir = (cfg_path.parent / cfg["output"]["posts_dir"]).resolve()
    return posts_dir.parent / "_data"


_TAKE_RE = re.compile(
    r"## My take \(reflective voice\)(.*?)(?=^##|\Z)",
    re.DOTALL | re.MULTILINE,
)
_SOURCE_RE = re.compile(r"Source:\s*\[([^\]]*)\]\(([^)]+)\)")


def reflect_once(config_path: str) -> None:
    cfg_path = Path(config_path).resolve()
    cfg = yaml.safe_load(cfg_path.read_text())
    posts_dir = (cfg_path.parent / cfg["output"]["posts_dir"]).resolve()
    data_dir = posts_dir.parent / "_data"
    data_dir.mkdir(parents=True, exist_ok=True)

    tags: list[str] = cfg.get("output", {}).get("tags", [])

    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=7)

    # --- Scan posts modified in last 7 days ---
    takes: list[str] = []
    source_urls: list[str] = []

    for md_file in sorted(posts_dir.glob("*.md")):
        mtime = md_file.stat().st_mtime
        modified = datetime.fromtimestamp(mtime, tz=timezone.utc)
        if modified < cutoff:
            continue
        content = md_file.read_text(encoding="utf-8", errors="replace")
        for m in _TAKE_RE.finditer(content):
            snippet = m.group(1).strip()
            if snippet:
                takes.append(snippet)
        for m in _SOURCE_RE.finditer(content):
            url = m.group(2).strip()
            if url and url not in source_urls:
                source_urls.append(url)

    # --- Concepts summary ---
    concepts_path = data_dir / "concepts.json"
    concepts: dict[str, Any] = {}
    if concepts_path.exists():
        try:
            concepts = json.loads(concepts_path.read_text())
        except Exception:
            concepts = {}

    top_concepts = sorted(
        ((t, info.get("count", 0)) for t, info in concepts.items() if isinstance(info, dict)),
        key=lambda x: x[1],
        reverse=True,
    )[:10]

    # --- Build post body ---
    start_date = cutoff.strftime("%Y-%m-%d")
    end_date = now.strftime("%Y-%m-%d")

    take_section = "\n\n---\n\n".join(takes) if takes else "_No reflective sections found this week._"

    if source_urls:
        sources_md = "\n".join(f"- {url}" for url in source_urls[:20])
    else:
        sources_md = "_No sources recorded this week._"

    if top_concepts:
        concepts_md = ", ".join(f"**{t}** ({c})" for t, c in top_concepts)
    else:
        concepts_md = "_No concept data available._"

    body = f"""## Week in review

This is an automated weekly reflection covering posts published between {start_date} and {end_date}.

## Top concepts this week

{concepts_md}

## Highlights from my take sections

{take_section}

## Sources this week

{sources_md}

## My take (reflective voice)

Reading through this week's material, the recurring themes point toward rapid iteration in AI tooling and the growing importance of interpretability. Each source adds a piece to an ongoing puzzle about where machine learning is heading.
"""

    post = Post(
        title=f"Ghost weekly reflection: {start_date} to {end_date}",
        date=now,
        tags=tags + ["weekly-reflection"],
        body_md=body,
    )
    out_path = write_new_post(posts_dir, post)
    print(f"[reflector] wrote {out_path}")

    # --- Update memory.json ---
    post_count = len(list(posts_dir.glob("*.md")))
    memory = {
        "last_reflection": now.isoformat(),
        "reflection_period": {"start": start_date, "end": end_date},
        "top_concepts": [{"term": t, "count": c} for t, c in top_concepts],
        "post_count": post_count,
    }
    memory_path = data_dir / "memory.json"
    memory_path.write_text(json.dumps(memory, indent=2), encoding="utf-8")
    print(f"[reflector] updated {memory_path}")
