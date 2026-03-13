from __future__ import annotations

import logging
import re
import socket
import time
from dataclasses import dataclass
from functools import lru_cache
from ipaddress import ip_address
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

    def _sleep_if_needed(self, host: str) -> None:
        now = time.time()
        sleep_for = self._delay_s - (now - self._last_request_ts)
        if sleep_for > 0:
            time.sleep(sleep_for)

        if host:
            last_host_ts = self._last_request_by_host.get(host, 0.0)
            host_sleep = self._delay_s - (time.time() - last_host_ts)
            if host_sleep > 0:
                time.sleep(host_sleep)

    def _mark_request(self, host: str) -> None:
        now = time.time()
        self._last_request_ts = now
        if host:
            self._last_request_by_host[host] = now

    def _check_policy(self, url: str) -> None:
        u = normalize_url(url)
        p = urlparse(u)
        if p.scheme not in {"http", "https"}:
            raise PolicyError(f"Non-http(s) URL blocked: {u}")
        if p.scheme == "http" and not self._allow_http:
            raise PolicyError(f"HTTP URL blocked by policy: {u}")
        if p.username or p.password:
            raise PolicyError(f"Userinfo in URL blocked: {u}")
        if p.port is not None and p.port not in {80, 443}:
            raise PolicyError(f"Non-standard port blocked: {u}")
        h = (p.hostname or "").lower()
        if not h:
            raise PolicyError(f"URL has no hostname: {u}")
        if not self._host_allowed(h):
            raise PolicyError(f"Host blocked by policy: {h}")
        for d in self._disallowed_domains:
            if h == d or h.endswith("." + d):
                raise PolicyError(f"Domain blocked by policy: {h}")
        if self._obey_robots and not self._robots_allows(u):
            raise PolicyError(f"robots.txt disallows: {u}")

    @lru_cache(maxsize=2048)
    def _host_allowed(self, host: str) -> bool:
        h = host.strip().lower().rstrip(".")
        if not h:
            return False
        if h in {"localhost"} or h.endswith(".local"):
            return False
        if h in {"metadata.google.internal"}:
            return False

        # If it's an IP literal, check directly.
        try:
            ip = ip_address(h)
            return self._ip_allowed(ip)
        except ValueError:
            pass

        # Resolve and block private/loopback/link-local/etc. Fail closed if DNS fails.
        try:
            infos = socket.getaddrinfo(h, None, proto=socket.IPPROTO_TCP)
        except OSError as e:
            logging.warning("DNS resolution failed for host %s: %s", h, e)
            return False

        for fam, _type, _proto, _canon, sockaddr in infos:
            try:
                if fam == socket.AF_INET:
                    ip = ip_address(sockaddr[0])
                elif fam == socket.AF_INET6:
                    ip = ip_address(sockaddr[0])
                else:
                    continue
            except ValueError:
                return False
            if not self._ip_allowed(ip):
                return False
        return True

    def _ip_allowed(self, ip) -> bool:  # type: ignore[no-untyped-def]
        if ip.is_loopback or ip.is_private or ip.is_link_local:
            return False
        if ip.is_multicast or ip.is_unspecified or ip.is_reserved:
            return False
        return True

    @lru_cache(maxsize=256)
    def _robots_for(self, scheme: str, host: str) -> RobotFileParser:
        robots_url = f"{scheme}://{host}/robots.txt"
        rp = RobotFileParser()
        try:
            r = self._client.get(robots_url, follow_redirects=True)
            if r.status_code == 200:
                rp.parse(r.text.splitlines())
            elif r.status_code == 404:
                # No robots.txt: standard convention is to allow all crawling.
                rp.parse(["User-agent: *", "Allow: /"])
            else:
                # Other non-200 (e.g. 500, 403): fail closed.
                logging.warning("robots.txt returned %s for %s; assuming disallowed", r.status_code, robots_url)
                rp.parse(["User-agent: *", "Disallow: /"])
        except (httpx.RequestError, OSError) as e:
            logging.warning("robots.txt fetch failed for %s: %s", robots_url, e)
            # Network failure: fail closed.
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

        current = url
        redirects = 0
        while True:
            host = (urlparse(current).hostname or "").lower()
            self._sleep_if_needed(host)

            try:
                with self._client.stream("GET", current) as r:
                    self._mark_request(host)

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

                    ct = r.headers.get("content-type")
                    if looks_like_binary(ct):
                        raise PolicyError(f"Non-text content-type blocked: {ct}")

                    # Read a bounded amount to avoid untrusted-size responses.
                    max_bytes = max(4096, min(self._max_chars * 4, 2_000_000))
                    buf = bytearray()
                    for chunk in r.iter_bytes():
                        if not chunk:
                            continue
                        take = max_bytes - len(buf)
                        if take <= 0:
                            break
                        buf.extend(chunk[:take])
                        if len(buf) >= max_bytes:
                            break

                    enc = r.encoding or "utf-8"
                    text = bytes(buf).decode(enc, errors="replace")
                    if len(text) > self._max_chars:
                        text = text[: self._max_chars]

                    final_url = normalize_url(str(r.url))
                    if final_url != current:
                        self._check_policy(final_url)

                    return FetchResult(
                        url=final_url,
                        status_code=r.status_code,
                        content_type=ct,
                        text=text,
                    )
            except httpx.RequestError as e:
                raise PolicyError(f"Fetch failed: {current}: {e}") from e

