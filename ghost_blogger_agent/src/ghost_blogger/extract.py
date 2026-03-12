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


def _clean_text(s: str) -> str:
    t = s.replace("\r\n", "\n").replace("\r", "\n")
    t = _WS_RE.sub("\n", t)
    t = _NL_RE.sub("\n\n", t)
    return t.strip()


def extract_readable_text(html: str) -> ExtractedPage:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "svg", "canvas", "form", "input", "button"]):
        tag.decompose()

    for tag in soup.find_all(["nav", "header", "footer", "aside"]):
        tag.decompose()

    title = None
    if soup.title and soup.title.string:
        title = _clean_text(soup.title.string)

    main = soup.find("article") or soup.find("main") or soup.body or soup
    text = main.get_text("\n", strip=True)
    text = _clean_text(text)
    return ExtractedPage(title=title, text=text)
