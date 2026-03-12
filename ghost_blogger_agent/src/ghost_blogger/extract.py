from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class ExtractedPage:
    title: "str | None"
    text: str


_WS_RE = re.compile(r"[ \t]+\n")
_NL_RE = re.compile(r"\n{3,}")
_BOILER_RE = re.compile(r"^\s*jump\s+to\s+(content|navigation|search)\s*$", re.IGNORECASE)


def _clean_text(s: str) -> str:
    t = s.replace("\r\n", "\n").replace("\r", "\n")
    t = _WS_RE.sub("\n", t)
    t = _NL_RE.sub("\n\n", t)
    # Drop common UI boilerplate lines (esp. Wikipedia).
    lines = [ln.strip() for ln in t.splitlines()]
    lines = [ln for ln in lines if ln and not _BOILER_RE.match(ln)]
    return "\n".join(lines).strip()


def extract_readable_text(html: str) -> ExtractedPage:
    # Use stdlib parser to avoid requiring native deps (works on GitHub Actions by default).
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "canvas", "form", "input", "button"]):
        tag.decompose()

    for tag in soup.find_all(["nav", "header", "footer", "aside"]):
        tag.decompose()

    title = None
    # Prefer page-specific headings when available.
    h1 = soup.select_one("h1#firstHeading") or soup.select_one("h1.title") or soup.find("h1")
    if h1:
        t = _clean_text(h1.get_text(" ", strip=True))
        t = re.sub(r"^\s*Title:\s*", "", t, flags=re.IGNORECASE)
        if t:
            title = t
    if not title and soup.title and soup.title.string:
        title = _clean_text(soup.title.string)

    # Site-specific main-content hints (helps avoid navigation-heavy pages).
    main = soup.select_one("blockquote.abstract")  # arXiv
    wiki = soup.select_one("#mw-content-text")  # Wikipedia
    if main is None and wiki is not None:
        # Reduce common Wikipedia noise.
        for el in wiki.select(
            ".mw-jump-link, .mw-editsection, sup.reference, .reference, .reflist, "
            ".navbox, .vertical-navbox, .catlinks, .infobox, .metadata, .mbox"
        ):
            el.decompose()
        main = wiki
    if main is None:
        main = soup.find("article") or soup.find("main") or soup.body or soup
    text = main.get_text("\n", strip=True)
    text = _clean_text(text)
    if len(text) > 20_000:
        text = text[:20_000]
    return ExtractedPage(title=title, text=text)
