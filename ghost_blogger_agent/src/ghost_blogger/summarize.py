from __future__ import annotations

import math
import re
from collections import Counter


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z']+")


def _sentences(text: str) -> list[str]:
    sents = _SENT_SPLIT.split(text.strip())
    return [s.strip() for s in sents if len(s.strip()) > 0]


def summarize(text: str, *, max_sentences: int = 7) -> str:
    sents = _sentences(text)
    if not sents:
        return ""
    if len(sents) <= max_sentences:
        return " ".join(sents)

    words = [w.lower() for w in _WORD_RE.findall(text)]
    if not words:
        return " ".join(sents[:max_sentences])
    freq = Counter(words)

    def score(sent: str, position: int) -> float:
        ws = [w.lower() for w in _WORD_RE.findall(sent)]
        if not ws:
            return 0.0
        base = sum(freq[w] for w in ws) / math.sqrt(len(ws))
        return base * (1.0 / (1 + position * 0.15))

    scored = [(i, score(s, i), s) for i, s in enumerate(sents)]
    scored.sort(key=lambda t: t[1], reverse=True)
    chosen = sorted(scored[:max_sentences], key=lambda t: t[0])
    return " ".join(s for _, __, s in chosen)

