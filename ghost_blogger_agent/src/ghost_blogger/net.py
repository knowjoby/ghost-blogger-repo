from __future__ import annotations

import logging
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
        # Conservative defaults: we manually validate redirects and we obey robots.txt.
        self._client = httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
            follow_redirects=False,
            timeout=httpx.Timeout(timeout_s),
        )
        self._delay_s = float(delay_s)
        self._allow_http = bool(allow_http)
        self._disallowed_domains = {d.lower().lstrip(".") for d in disallowed_domains}
        self._obey_robots = bool(obey_robots_txt)
        self._user_agent = user_agent
        self._max_chars = int(max_chars)
        self._last_request_ts = 0.0
        self._last_request_by_host: dict[str, float] = {}
        self._max_redirects = 5

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
                # Fail closed: if we cannot access robots.txt, assume disallowed.
                rp.parse(["User-agent: *", "Disallow: /"])
            else:
                rp.parse(r.text.splitlines())
        except Exception as e:
            logging.warning("robots.txt fetch failed for %s: %s", robots_url, e)
            # Fail closed: if robots.txt cannot be fetched/parsed, assume disallowed.
            rp.parse(["User-agent: *", "Disallow: /"])
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

        current = url
        redirects = 0
        while True:
            host = (urlparse(current).hostname or "").lower()
            if host:
                last_host_ts = self._last_request_by_host.get(host, 0.0)
                host_sleep = self._delay_s - (time.time() - last_host_ts)
                if host_sleep > 0:
                    time.sleep(host_sleep)

            r = self._client.get(current)
            now = time.time()
            self._last_request_ts = now
            if host:
                self._last_request_by_host[host] = now

            if r.status_code in {301, 302, 303, 307, 308} and "location" in r.headers:
                redirects += 1
                if redirects > self._max_redirects:
                    raise PolicyError(f"Too many redirects: {url}")
                nxt = str(httpx.URL(current).join(r.headers["location"]))
                nxt = normalize_url(nxt)
                # Validate the redirect target BEFORE fetching it.
                self._check_policy(nxt)
                current = nxt
                continue

            break

        final_url = normalize_url(str(r.url))
        if final_url != current:
            # Defensive: httpx may still normalize; re-check policy.
            self._check_policy(final_url)
        ct = r.headers.get("content-type")
        if looks_like_binary(ct):
            raise PolicyError(f"Non-text content-type blocked: {ct}")
        text = r.text
        if len(text) > self._max_chars:
            text = text[: self._max_chars]
        return FetchResult(url=final_url, status_code=r.status_code, content_type=ct, text=text)
