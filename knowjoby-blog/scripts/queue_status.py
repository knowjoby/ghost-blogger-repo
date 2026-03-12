#!/usr/bin/env python3
"""
Queue Status - inspect and maintain data/news_queue.json.

Usage:
  python scripts/queue_status.py
  python scripts/queue_status.py pending
  python scripts/queue_status.py posted
  python scripts/queue_status.py clear-old
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

BASE_DIR = Path(__file__).parent.parent
QUEUE_FILE = BASE_DIR / "data" / "news_queue.json"
RUN_LOG_FILE = BASE_DIR / "_data" / "run_log.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def save_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2))


def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f" {text}")
    print(f"{'=' * 60}")


def show_config(config: Dict[str, Any]) -> None:
    print_header("CONFIGURATION")
    if not config:
        print("  (none)")
        return
    for key, value in config.items():
        print(f"  {key}: {value}")


def show_daily_usage(usage_list: List[Dict[str, Any]], limit: int = 10) -> None:
    print_header("DAILY USAGE")
    if not usage_list:
        print("  No usage data")
        return

    usage_list = sorted(usage_list, key=lambda x: x.get("date", ""), reverse=True)
    for usage in usage_list[:limit]:
        date = usage.get("date", "unknown")
        posts = usage.get("posts", 0)
        processed = usage.get("items_processed", 0)
        print(f"  {date}: {posts} posts from {processed} items")


def _score(item: Dict[str, Any]) -> int:
    try:
        return int(item.get("score", 0) or 0)
    except Exception:
        return 0


def show_items(items: List[Dict[str, Any]], *, title: str, limit: int = 15, reverse: bool = True) -> None:
    print_header(title)
    if not items:
        print("  (empty)")
        return

    sorted_items = sorted(items, key=_score, reverse=reverse)
    for i, item in enumerate(sorted_items[:limit], start=1):
        score = _score(item)
        t = (item.get("title", "") or "").strip()
        url = (item.get("url", "") or "").strip()
        companies = item.get("companies") or []
        topics = item.get("topics") or []
        tags = [*companies, *topics]
        tags_str = f" [{', '.join(tags)}]" if tags else ""
        print(f"  {i:2d}. [{score:3d}] {t[:80]}{tags_str}")
        if url:
            print(f"      {url}")


def show_recent_runs(run_log: List[Dict[str, Any]], limit: int = 5) -> None:
    print_header("RECENT RUNS")
    if not run_log:
        print("  No run data")
        return

    for entry in run_log[-limit:]:
        ran_at = (entry.get("ran_at", "") or "")[:19]
        candidates = entry.get("candidates_found", 0)
        posts = entry.get("posts_created", 0)
        queued = entry.get("queued", 0)
        print(f"  {ran_at} - Candidates: {candidates}, Posts: {posts}, Queued: {queued}")


def parse_date_utc(value: str) -> Optional[datetime]:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(value[: len(fmt)], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass
    return None


def clear_old_pending(queue: Dict[str, Any], keep_days: int = 14) -> int:
    pending = list(queue.get("pending", []) or [])
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=keep_days)
    kept: List[Dict[str, Any]] = []
    removed = 0
    for item in pending:
        fetched_at = parse_date_utc(str(item.get("fetched_at", "") or ""))
        if fetched_at and fetched_at.date() < cutoff:
            removed += 1
            continue
        kept.append(item)
    queue["pending"] = kept
    return removed


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(argv) if argv is not None else sys.argv[1:]
    cmd = argv[0] if argv else "all"

    queue_data = load_json(
        QUEUE_FILE,
        {"queue": [], "config": {}, "pending": [], "posted": [], "daily_usage": []},
    )
    run_log = load_json(RUN_LOG_FILE, [])

    if cmd == "clear-old":
        removed = clear_old_pending(queue_data, keep_days=14)
        save_json(QUEUE_FILE, queue_data)
        print(f"Removed {removed} old pending items.")
        return 0

    config = queue_data.get("config", {}) or {}
    pending = list(queue_data.get("pending", []) or [])
    posted = list(queue_data.get("posted", []) or [])
    usage = list(queue_data.get("daily_usage", []) or [])

    if cmd in ("all", ""):
        show_config(config)
        show_daily_usage(usage)
        show_items(pending, title="PENDING (top 15)", limit=15)
        show_items(posted, title="POSTED (top 15 by score)", limit=15)
        show_recent_runs(run_log)
        return 0

    if cmd == "pending":
        show_items(pending, title="PENDING (top 50)", limit=50)
        return 0

    if cmd == "posted":
        show_items(posted, title="POSTED (top 50 by score)", limit=50)
        return 0

    print("Unknown command. Use: pending | posted | clear-old")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
