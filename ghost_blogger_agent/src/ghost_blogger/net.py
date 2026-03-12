from __future__ import annotations

import re
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Iterable
from urllib.parse import urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx


class PolicyError(RuntimeError):
    pass


def normalize_url(url: str) -> str:
    u = url.strip()
    p = urlparse(u)
    p = p._replace(fragment="")
    # Basic canonicalization: drop default ports
    netloc = p.netloc
    if netloc.endswith(":80") and p.scheme == "http":
        netloc = netloc[:-3]
    if netloc.endswith(":443") and p.scheme == "https":
        netloc = netloc[:-4]
    p = p._replace(netloc=netloc)
    return urlunparse(p)


def hostname(url: str) -> str:
    return urlparse(url).hostname or ""


def is_http_url(url: str) -> bool:
    return urlparse(url).scheme in {"http", "https"}


def looks_like_binary(content_type: "str | None") -> bool:
    if not content_type:
        return False
    ct = content_type.split(";", 1)[0].strip().lower()
    if ct.startswith("text/"):
        return False
    return ct not in {"application/xml", "application/xhtml+xml", "application/rss+xml", "application/atom+xml"}


def redact_pii_like(text: str) -> str:
    t = text
    t = re.sub(r"\b[\w.\-+]+@[\w.\-]+\.\w+\b", "[redacted-email]", t)
    t = re.sub(r"\b\d{3}[-.\s]?\d{2,3}[-.\s]?\d{4}\b", "[redacted-phone]", t)
    return t


@dataclass(frozen=True)
class FetchResult:
    url: str
    status_code: int
    content_type: "str | None"
    text: str


class SafeFetcher:
    def __init__(
        self,
        *,
        user_agent: str,
        timeout_s: int,
        delay_s: float,
        allow_http: bool,
        disallowed_domains: Iterable[str],
        obey_robots_txt: bool,
        max_chars: int,
    ) -> None:
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            follow_redirects=True,
            timeout=httpx.Timeout(timeout_s),
        )
        self._delay_s = float(delay_s)
        self._allow_http = bool(allow_http)
        self._disallowed_domains = {d.lower().lstrip(".") for d in disallowed_domains}
        self._obey_robots = bool(obey_robots_txt)
        self._user_agent = user_agent
        self._max_chars = int(max_chars)
        self._last_request_ts = 0.0

    def close(self) -> None:
        self._client.close()

    def _check_policy(self, url: str) -> None:
        u = normalize_url(url)
        p = urlparse(u)
        if p.scheme not in {"http", "https"}:
            raise PolicyError(f"Non-http(s) URL blocked: {u}")
        if p.scheme == "http" and not self._allow_http:
            raise PolicyError(f"HTTP URL blocked by policy: {u}")
        h = (p.hostname or "").lower()
        if not h:
            raise PolicyError(f"URL has no hostname: {u}")
        for d in self._disallowed_domains:
            if h == d or h.endswith("." + d):
                raise PolicyError(f"Domain blocked by policy: {h}")
        if self._obey_robots and not self._robots_allows(u):
            raise PolicyError(f"robots.txt disallows: {u}")

    @lru_cache(maxsize=256)
    def _robots_for(self, scheme: str, host: str) -> RobotFileParser:
        robots_url = f"{scheme}://{host}/robots.txt"
        rp = RobotFileParser()
        try:
            r = self._client.get(robots_url)
            if r.status_code >= 400:
                rp.parse([])
            else:
                rp.parse(r.text.splitlines())
        except Exception:
            rp.parse([])
        return rp

    def _robots_allows(self, url: str) -> bool:
        p = urlparse(url)
        host = p.hostname or ""
        if not host:
            return False
        rp = self._robots_for(p.scheme, host)
        return bool(rp.can_fetch(self._user_agent, url))

    def get_text(self, url: str) -> FetchResult:
        url = normalize_url(url)
        self._check_policy(url)

        now = time.time()
        sleep_for = self._delay_s - (now - self._last_request_ts)
        if sleep_for > 0:
            time.sleep(sleep_for)

        r = self._client.get(url)
        self._last_request_ts = time.time()
        ct = r.headers.get("content-type")
        if looks_like_binary(ct):
            raise PolicyError(f"Non-text content-type blocked: {ct}")
        text = r.text
        if len(text) > self._max_chars:
            text = text[: self._max_chars]
        return FetchResult(url=str(r.url), status_code=r.status_code, content_type=ct, text=text)
