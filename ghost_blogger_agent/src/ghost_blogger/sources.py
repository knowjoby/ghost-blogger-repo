from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Iterable

import feedparser

from ghost_blogger.net import PolicyError, SafeFetcher, normalize_url


@dataclass(frozen=True)
class SourceItem:
    url: str
    title: "str | None" = None
    source: "str | None" = None


def iter_feed_items(fetcher: SafeFetcher, feed_url: str) -> list[SourceItem]:
    try:
        res = fetcher.get_text(feed_url)
    except PolicyError:
        return []

    parsed = feedparser.parse(res.text)
    if getattr(parsed, "bozo", 0):
        ex = getattr(parsed, "bozo_exception", None)
        logging.warning("Malformed feed skipped: %s (%s)", feed_url, ex)
        return []
    out: list[SourceItem] = []
    feed_title = getattr(parsed.feed, "title", None)
    for e in parsed.entries[:30]:
        link = getattr(e, "link", None)
        if not link:
            continue
        title = getattr(e, "title", None)
        out.append(SourceItem(url=normalize_url(link), title=title, source=feed_title))
    return out


def dedupe_items(items: Iterable[SourceItem]) -> list[SourceItem]:
    seen: set[str] = set()
    out: list[SourceItem] = []
    for it in items:
        u = normalize_url(it.url)
        if u in seen:
            continue
        seen.add(u)
        out.append(SourceItem(url=u, title=it.title, source=it.source))
    return out
