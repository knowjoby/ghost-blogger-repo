from __future__ import annotations

import json
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml


def _data_dir(config_path: str) -> Path:
    cfg_path = Path(config_path).resolve()
    cfg = yaml.safe_load(cfg_path.read_text())
    posts_dir = (cfg_path.parent / cfg["output"]["posts_dir"]).resolve()
    return posts_dir.parent / "_data"


def _probe_feed(url: str, timeout: int = 15) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            status = r.status
            reachable = status < 400
    except Exception:
        reachable = False
        status = 0
    return {"reachable": reachable, "status_code": status}


def analyse_once(config_path: str) -> None:
    cfg_path = Path(config_path).resolve()
    cfg = yaml.safe_load(cfg_path.read_text())
    data_dir = _data_dir(config_path)
    data_dir.mkdir(parents=True, exist_ok=True)

    analyst_cfg = cfg.get("analyst") or {}
    lookback_days = analyst_cfg.get("lookback_days", 7)

    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=lookback_days)

    # --- runs.json ---
    runs_path = data_dir / "runs.json"
    runs: list[dict] = []
    if runs_path.exists():
        try:
            runs = json.loads(runs_path.read_text())
        except Exception:
            runs = []

    recent_runs = []
    for r in runs:
        try:
            ts = datetime.fromisoformat(r["timestamp"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                recent_runs.append(r)
        except Exception:
            pass

    if recent_runs:
        successes = sum(1 for r in recent_runs if r.get("post_written", False))
        run_success_rate = round(successes / len(recent_runs), 4)
    else:
        run_success_rate = 0.0

    # --- concepts.json ---
    concepts_path = data_dir / "concepts.json"
    concepts: dict[str, Any] = {}
    if concepts_path.exists():
        try:
            concepts = json.loads(concepts_path.read_text())
        except Exception:
            concepts = {}

    # Compute top concepts in lookback window and concept gaps
    cutoff_3d = now - timedelta(days=3)
    top_concepts_7d: list[str] = []
    concept_gaps: list[str] = []
    suggested_seed_urls: list[str] = []

    for term, info in concepts.items():
        if not isinstance(info, dict):
            continue
        count = info.get("count", 0)
        posts = info.get("posts", [])
        # concept gap: appeared once, never got a dedicated post
        if count == 1:
            concept_gaps.append(term)
            slug = term.strip().replace(" ", "_")
            suggested_seed_urls.append(f"https://en.wikipedia.org/wiki/{slug}")

    # top concepts by count in last 7d (approximation: use overall count, sorted desc)
    sorted_concepts = sorted(
        ((term, info.get("count", 0)) for term, info in concepts.items() if isinstance(info, dict)),
        key=lambda x: x[1],
        reverse=True,
    )
    top_concepts_7d = [t for t, _ in sorted_concepts[:10]]

    # --- feed health ---
    feeds: list[str] = cfg.get("sources", {}).get("feeds", [])
    feed_health: dict[str, Any] = {}
    for feed_url in feeds:
        feed_health[feed_url] = _probe_feed(feed_url)

    # Suggested removes: feeds that are unreachable
    suggested_feed_removes = [url for url, h in feed_health.items() if not h["reachable"]]

    analysis = {
        "generated": now.isoformat(),
        "feed_health": feed_health,
        "top_concepts_7d": top_concepts_7d,
        "concept_gaps": concept_gaps[:20],
        "suggested_seed_urls": suggested_seed_urls[:20],
        "suggested_feed_removes": suggested_feed_removes,
        "run_success_rate_7d": run_success_rate,
    }

    out_path = data_dir / "analysis.json"
    out_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"[analyst] wrote {out_path}")
