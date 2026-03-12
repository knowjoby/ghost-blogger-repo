#!/usr/bin/env python3
"""
AI news link-post generator for the Jekyll blog.

- Fetches recent AI-related stories via DuckDuckGo News (no API key required)
- Scores + dedupes stories using keyword rules in scripts/config.py
- Writes minimal link-posts into _posts/
- Updates data/news_queue.json and _data/run_log.json

GitHub Action entrypoint: .github/workflows/daily-news.yml
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# Ensure repo root is importable when running as a script.
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.config import detect_companies, detect_topics, get_company_tier


POSTS_DIR = REPO_ROOT / "_posts"
QUEUE_FILE = REPO_ROOT / "data" / "news_queue.json"
RUN_LOG_FILE = REPO_ROOT / "_data" / "run_log.json"
PUBLIC_QUEUE_FILE = REPO_ROOT / "_data" / "news_queue_public.json"


DEFAULT_SEARCH_QUERIES = [
    "AI model release news",
    "OpenAI OR Anthropic OR Google DeepMind OR Microsoft OR Meta OR xAI AI news",
    "AI safety policy regulation controversy funding partnership",
]


AI_GENERIC_HINTS = [
    "artificial intelligence",
    "generative ai",
    "genai",
    "large language model",
    "llm",
    "foundation model",
    "chatbot",
    "ai agent",
]


def now_ist_str() -> str:
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S IST")


def parse_any_date(s: str) -> Optional[datetime]:
    if not s:
        return None

    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            dt = datetime.strptime(s[: len(fmt)], fmt)
            return dt.replace(tzinfo=timezone.utc)
        except Exception:
            pass

    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    url = re.sub(r"#.*$", "", url)
    url = re.sub(r"[?&]utm_[^=&]+=[^&]+", "", url, flags=re.IGNORECASE)
    url = re.sub(r"[?&]ref=[^&]+", "", url, flags=re.IGNORECASE)
    url = re.sub(r"[?&]source=[^&]+", "", url, flags=re.IGNORECASE)
    url = re.sub(r"[?&]$", "", url)
    return url


def slugify(title: str, max_len: int = 70) -> str:
    s = (title or "").lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    if not s:
        s = "ai-news"
    return s[:max_len].rstrip("-")


def title_similarity(a: str, b: str) -> float:
    a = (a or "").lower().strip()
    b = (b or "").lower().strip()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    aw = set(re.findall(r"[a-z0-9]+", a))
    bw = set(re.findall(r"[a-z0-9]+", b))
    if not aw or not bw:
        return 0.0
    overlap = len(aw & bw)
    denom = max(len(aw), len(bw))
    return overlap / denom


def load_queue() -> Dict[str, Any]:
    if not QUEUE_FILE.exists():
        return {
            "queue": [],
            "config": {"daily_post_limit": 5, "min_score_to_post": 50, "max_words_per_post": 200},
            "pending": [],
            "posted": [],
            "daily_usage": [],
        }
    return json.loads(QUEUE_FILE.read_text())


def save_queue(queue: Dict[str, Any]) -> None:
    QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, sort_keys=False))

def publish_public_queue(queue: Dict[str, Any]) -> None:
    """
    Publish a sanitized, deduplicated view of the queue for the UI.
    GitHub Pages can read _data/*.json but not arbitrary /data files.
    """
    posted = list(queue.get("posted", []) or [])
    pending = list(queue.get("pending", []) or [])

    def _norm(u: str) -> str:
        return normalize_url(u or "")

    posted_urls: Set[str] = set(_norm(p.get("url", "")) for p in posted if p.get("url"))
    out_pending: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for item in pending:
        url = _norm(item.get("url", ""))
        if not url or url in posted_urls or url in seen:
            continue
        seen.add(url)
        out_pending.append(
            {
                "title": item.get("title", ""),
                "url": url,
                "score": int(item.get("score", 0) or 0),
                "fetched_at": item.get("fetched_at", ""),
                "source": item.get("source", ""),
                "companies": item.get("companies") or [],
                "topics": item.get("topics") or [],
            }
        )

    def _pending_sort_key(item: Dict[str, Any]) -> Tuple[str, int, str]:
        fetched_at = str(item.get("fetched_at", "") or "")
        # sort newest first; YYYY-MM-DD strings sort lexicographically
        return (fetched_at, int(item.get("score", 0) or 0), str(item.get("url", "") or ""))

    out_pending = sorted(out_pending, key=_pending_sort_key, reverse=True)

    payload = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pending_count": len(out_pending),
        # Keep large enough to include the full queue in the UI (Archives -> Queue).
        # Jekyll reads _data/*.json at build time; keep this bounded to avoid runaway sizes.
        "pending": out_pending[:2000],
    }

    PUBLIC_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_QUEUE_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False))


def load_run_log() -> List[Dict[str, Any]]:
    if not RUN_LOG_FILE.exists():
        return []
    try:
        return json.loads(RUN_LOG_FILE.read_text())
    except Exception:
        return []


def save_run_log(entries: List[Dict[str, Any]]) -> None:
    RUN_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    RUN_LOG_FILE.write_text(json.dumps(entries[-50:], indent=2, ensure_ascii=False))


def write_run_log(*, candidates_found: int, posts_written: List[Dict[str, Any]], queued_count: int, feed_stats: Dict[str, Any]) -> None:
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    if event == "schedule":
        triggered_by = "Scheduled"
    elif event == "workflow_dispatch":
        triggered_by = "Manual (GitHub)"
    else:
        triggered_by = "Manual (local)"

    entry = {
        "ran_at": now_ist_str(),
        "triggered_by": triggered_by,
        "candidates_found": candidates_found,
        "posts_created": len(posts_written),
        "queued": queued_count,
        "feeds": feed_stats,
        "posts": [
            {
                "title": p.get("title", ""),
                "file": p.get("file", ""),
                "score": p.get("score", 0),
                "tags": p.get("tags", []),
            }
            for p in posts_written
        ],
    }

    log = load_run_log()
    log.append(entry)
    save_run_log(log)


def is_ai_relevant(title: str, snippet: str) -> Tuple[List[str], List[str]]:
    combined = f"{title} {snippet}".strip()
    companies = detect_companies(combined)
    topics = detect_topics(combined)
    if companies or topics:
        return companies, topics

    combined_lower = combined.lower()
    if any(hint in combined_lower for hint in AI_GENERIC_HINTS):
        return [], ["ai"]

    return [], []


def score_story(*, title: str, snippet: str, companies: Sequence[str], topics: Sequence[str], published_at: Optional[datetime]) -> int:
    score = 0

    if published_at:
        age_days = (datetime.now(timezone.utc) - published_at).days
        if age_days <= 0:
            score += 25
        elif age_days <= 1:
            score += 22
        elif age_days <= 3:
            score += 16
        elif age_days <= 7:
            score += 10
        else:
            score -= 15

    title_lower = (title or "").lower()
    combined_lower = f"{title} {snippet}".lower()

    for c in companies:
        tier = get_company_tier(c)
        score += 18 if tier == 1 else 10
        if c in title_lower:
            score += 6

    for t in topics:
        score += 3 if t == "ai" else 8
        if t in title_lower:
            score += 3

    if any(
        k in combined_lower
        for k in (
            "release",
            "launch",
            "announc",
            "introduc",
            "open-sourc",
            "weights",
            "funding",
            "raises",
            "acquires",
            "partnership",
            "policy",
            "regulation",
            "ban",
        )
    ):
        score += 6
    if any(k in combined_lower for k in ("rumor", "leak", "reportedly", "unconfirmed")):
        score -= 4

    return max(0, min(100, score))


def fetch_ddg_news(*, queries: Sequence[str], max_results_per_query: int, timelimit: str) -> List[Dict[str, Any]]:
    DDGS = None
    # duckduckgo-search was renamed to ddgs; support both.
    try:
        from ddgs import DDGS as _DDGS  # type: ignore

        DDGS = _DDGS
    except Exception:
        try:
            from duckduckgo_search import DDGS as _DDGS  # type: ignore

            DDGS = _DDGS
        except Exception as e:
            raise RuntimeError("DDG client missing. Install with: pip install ddgs duckduckgo-search") from e

    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    with DDGS() as ddgs:
        for query in queries:
            try:
                items = ddgs.news(keywords=query, max_results=max_results_per_query, timelimit=timelimit)
                for r in items:
                    url = normalize_url(r.get("url", ""))
                    title = html.unescape((r.get("title", "") or "").strip())
                    if not url or not title:
                        continue
                    if url in seen:
                        continue
                    seen.add(url)
                    results.append(
                        {
                            "title": title,
                            "url": url,
                            "source": (r.get("source", "") or "").strip(),
                            "date": (r.get("date", "") or "").strip(),
                            "snippet": html.unescape((r.get("body", "") or "").strip()),
                        }
                    )
            except Exception:
                continue

    return results


DEFAULT_RSS_FEEDS: Sequence[Tuple[str, str]] = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("VentureBeat", "https://feeds.feedburner.com/venturebeat/SZYF"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("Wired", "https://www.wired.com/feed/rss"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google AI", "https://blog.google/technology/ai/rss/"),
    ("Microsoft AI", "https://blogs.microsoft.com/ai/feed/"),
    ("Hugging Face", "https://huggingface.co/blog/feed.xml"),
]


def load_rss_sources() -> Sequence[Tuple[str, str]]:
    """
    Load RSS sources from _data/rss_sources.json if present, otherwise fall back.
    Kept in _data so Jekyll can render the same list on /sources/.
    """
    sources_file = REPO_ROOT / "_data" / "rss_sources.json"
    if not sources_file.exists():
        return DEFAULT_RSS_FEEDS

    try:
        data = json.loads(sources_file.read_text())
        feeds: List[Tuple[str, str]] = []
        for item in data:
            name = (item.get("name") or "").strip()
            url = (item.get("url") or "").strip()
            if name and url:
                feeds.append((name, url))
        return feeds or DEFAULT_RSS_FEEDS
    except Exception:
        return DEFAULT_RSS_FEEDS


def fetch_rss_news(*, max_age_days: int = 7) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    try:
        import feedparser  # type: ignore
    except Exception as e:
        raise RuntimeError("feedparser is required. Install with: pip install feedparser") from e

    rss_feeds = load_rss_sources()
    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    results: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    stats: Dict[str, Any] = {"feeds_total": len(rss_feeds), "feeds_ok": 0, "feeds_failed": 0}

    for source, url in rss_feeds:
        try:
            parsed = feedparser.parse(url)
            if getattr(parsed, "bozo", 0):
                # bozo=1 indicates a parse issue, but entries may still exist.
                pass

            entries = getattr(parsed, "entries", []) or []
            if entries:
                stats["feeds_ok"] += 1
            else:
                stats["feeds_failed"] += 1

            for entry in entries:
                title = html.unescape((getattr(entry, "title", "") or "").strip())
                link = normalize_url((getattr(entry, "link", "") or "").strip())
                if not title or not link or link in seen:
                    continue

                summary = html.unescape((getattr(entry, "summary", "") or "").strip())

                published = (
                    getattr(entry, "published", "")
                    or getattr(entry, "updated", "")
                    or getattr(entry, "pubDate", "")
                    or ""
                )
                published_at = parse_any_date(str(published))
                if published_at and published_at < cutoff:
                    continue

                seen.add(link)
                results.append(
                    {
                        "title": title,
                        "url": link,
                        "source": source,
                        "date": published_at.isoformat() if published_at else "",
                        "snippet": summary[:300],
                    }
                )
        except Exception:
            stats["feeds_failed"] += 1
            continue

    return results, stats


def ensure_unique_filename(date_prefix: str, base_slug: str, url: str) -> Path:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    candidate = POSTS_DIR / f"{date_prefix}-{base_slug}.md"
    if not candidate.exists():
        return candidate

    suffix = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return POSTS_DIR / f"{date_prefix}-{base_slug}-{suffix}.md"


def write_link_post(*, title: str, url: str, source: str, tags: Sequence[str], score: int, published_at: Optional[datetime]) -> Path:
    dt = datetime.now(timezone.utc)
    date_prefix = dt.strftime("%Y-%m-%d")
    filename = ensure_unique_filename(date_prefix, slugify(title), url)

    original_date = ""
    if published_at:
        original_date = published_at.date().isoformat()

    tags_unique: List[str] = []
    for t in tags:
        if t and t not in tags_unique:
            tags_unique.append(t)

    safe_title = title.replace('"', '\\"')
    front_matter = [
        "---",
        "layout: post",
        f"title: \"{safe_title}\"",
        f"date: {dt.strftime('%Y-%m-%d %H:%M:%S %z')}",
        "categories: ai-news",
        f"tags: [{', '.join(tags_unique)}]",
        f"score: {int(score)}",
        f"link: {url}",
    ]
    if source:
        front_matter.append(f"source: {source}")
    if original_date:
        front_matter.append(f"original_date: {original_date}")
    front_matter.append("---")

    body = f"[Read on {source or 'source'}]({url})\n"
    filename.write_text("\n".join(front_matter) + "\n\n" + body)
    return filename


def get_today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def daily_usage_entry(daily_usage: List[Dict[str, Any]], today: str) -> Dict[str, Any]:
    for entry in daily_usage:
        if entry.get("date") == today:
            return entry
    entry = {"date": today, "posts": 0, "items_processed": 0, "estimated_tokens": 0}
    daily_usage.append(entry)
    return entry


def prune_old_pending(pending: List[Dict[str, Any]], *, keep_days: int) -> List[Dict[str, Any]]:
    cutoff = datetime.now(timezone.utc).date() - timedelta(days=keep_days)
    out: List[Dict[str, Any]] = []
    for p in pending:
        fetched_at = parse_any_date(str(p.get("fetched_at", "") or ""))
        if fetched_at and fetched_at.date() < cutoff:
            continue
        out.append(p)
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch, score, and publish AI news link posts.")
    parser.add_argument("--timelimit", default="w", help="DuckDuckGo News timelimit: d/w/m/y")
    parser.add_argument("--max-results-per-query", type=int, default=15)
    parser.add_argument("--dry-run", action="store_true", help="Do not write posts or update queue/run log.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    queue = load_queue()
    config = queue.get("config", {}) or {}

    daily_post_limit = int(config.get("daily_post_limit", 5))
    min_score_to_post = int(config.get("min_score_to_post", 50))

    pending: List[Dict[str, Any]] = list(queue.get("pending", []) or [])
    posted: List[Dict[str, Any]] = list(queue.get("posted", []) or [])
    daily_usage: List[Dict[str, Any]] = list(queue.get("daily_usage", []) or [])

    today = get_today_utc()
    usage = daily_usage_entry(daily_usage, today)

    remaining = max(0, daily_post_limit - int(usage.get("posts", 0) or 0))
    if remaining <= 0:
        if not args.dry_run:
            write_run_log(candidates_found=0, posts_written=[], queued_count=len(pending), feed_stats={"ddg": {"skipped": True}})
            queue["daily_usage"] = daily_usage
            save_queue(queue)
            publish_public_queue(queue)
        return 0

    known_urls: Set[str] = set()
    known_titles: List[str] = []
    for item in pending + posted:
        url = normalize_url(item.get("url") or item.get("source_url") or "")
        title = item.get("title", "") or ""
        if url:
            known_urls.add(url)
        if title:
            known_titles.append(title)

    raw: List[Dict[str, Any]] = []
    feed_stats: Dict[str, Any] = {"ddg": {}, "rss": {}}

    try:
        raw = fetch_ddg_news(
            queries=DEFAULT_SEARCH_QUERIES,
            max_results_per_query=args.max_results_per_query,
            timelimit=args.timelimit,
        )
        feed_stats["ddg"] = {"queries": len(DEFAULT_SEARCH_QUERIES), "raw": len(raw)}
    except Exception as e:
        feed_stats["ddg"] = {"error": str(e)}

    # GitHub-hosted runners sometimes get blocked by DDG; RSS is the reliable fallback.
    if not raw:
        try:
            raw, rss_stats = fetch_rss_news(max_age_days=7)
            feed_stats["rss"] = {"raw": len(raw), **rss_stats}
        except Exception as e:
            feed_stats["rss"] = {"error": str(e)}

    candidates: List[Dict[str, Any]] = []
    for r in raw:
        url = normalize_url(r.get("url", ""))
        if not url or url in known_urls:
            continue

        title = r.get("title", "")
        snippet = r.get("snippet", "")
        source = r.get("source", "")
        published_at = parse_any_date(r.get("date", ""))

        companies, topics = is_ai_relevant(title, snippet)
        if not companies and not topics:
            continue

        score = score_story(title=title, snippet=snippet, companies=companies, topics=topics, published_at=published_at)
        if score < 10:
            continue

        if any(title_similarity(title, t) >= 0.65 for t in known_titles):
            continue

        candidates.append(
            {
                "title": title,
                "url": url,
                "source": source,
                "published_at": published_at.isoformat() if published_at else "",
                "companies": companies,
                "topics": topics,
                "score": score,
            }
        )

        known_urls.add(url)
        known_titles.append(title)

    def sort_key(c: Dict[str, Any]) -> Tuple[int, int]:
        dt = parse_any_date(c.get("published_at", "")) or datetime(1970, 1, 1, tzinfo=timezone.utc)
        return (int(c.get("score", 0)), int(dt.timestamp()))

    candidates = sorted(candidates, key=sort_key, reverse=True)
    usage["items_processed"] = int(usage.get("items_processed", 0) or 0) + len(raw)

    posts_written: List[Dict[str, Any]] = []
    queued_count_before = len(pending)

    for c in candidates:
        if remaining <= 0:
            break
        if int(c["score"]) < min_score_to_post:
            continue

        tags = list(c["companies"]) + list(c["topics"])
        published_at = parse_any_date(c.get("published_at", ""))
        if args.dry_run:
            written_path = POSTS_DIR / "DRY_RUN.md"
        else:
            written_path = write_link_post(
                title=c["title"],
                url=c["url"],
                source=c.get("source", ""),
                tags=tags,
                score=int(c["score"]),
                published_at=published_at,
            )

        posted_entry = {
            "title": c["title"],
            "url": c["url"],
            "score": int(c["score"]),
            "file": str(written_path.relative_to(REPO_ROOT)),
            "posted_at": today,
            "companies": list(c["companies"]),
            "topics": list(c["topics"]),
        }
        posted.append(posted_entry)

        posts_written.append(
            {
                "title": c["title"],
                "file": posted_entry["file"],
                "score": int(c["score"]),
                "tags": tags,
            }
        )
        usage["posts"] = int(usage.get("posts", 0) or 0) + 1
        remaining -= 1

    posted_urls = {normalize_url(p.get("url", "")) for p in posted}
    for c in candidates:
        if normalize_url(c["url"]) in posted_urls:
            continue
        pending.append(
            {
                "title": c["title"],
                "url": c["url"],
                "score": int(c["score"]),
                "fetched_at": today,
                "source": c.get("source", ""),
                "companies": list(c["companies"]),
                "topics": list(c["topics"]),
                "company": (list(c["companies"]) or [""])[0],
                "topic": (list(c["topics"]) or [""])[0],
            }
        )

    pending = prune_old_pending(pending, keep_days=14)
    pending = sorted(pending, key=lambda x: int(x.get("score", 0) or 0), reverse=True)

    queue["config"] = {
        "daily_post_limit": daily_post_limit,
        "min_score_to_post": min_score_to_post,
        "max_words_per_post": int(config.get("max_words_per_post", 200)),
    }
    queue["pending"] = pending
    queue["posted"] = posted
    queue["daily_usage"] = daily_usage

    feed_stats.setdefault("ddg", {})
    feed_stats.setdefault("rss", {})
    # Preserve earlier feed_stats and add candidates count.
    if "ddg" in feed_stats and isinstance(feed_stats["ddg"], dict):
        feed_stats["ddg"]["candidates"] = len(candidates)
    if "rss" in feed_stats and isinstance(feed_stats["rss"], dict):
        feed_stats["rss"]["candidates"] = len(candidates)
    queued_after = len(pending)
    queued_added = max(0, queued_after - queued_count_before)

    if not args.dry_run:
        save_queue(queue)
        publish_public_queue(queue)
        write_run_log(candidates_found=len(candidates), posts_written=posts_written, queued_count=queued_added, feed_stats=feed_stats)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
