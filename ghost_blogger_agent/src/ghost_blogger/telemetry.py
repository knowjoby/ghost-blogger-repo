"""
telemetry.py — Write run history and concept stats to knowjoby-blog/_data/
so Jekyll can render live agent dashboards without any server.

Architecture note
-----------------
Every agent run appends one entry to   _data/runs.json      (capped at 100)
Every set of notes updates keyword counts in _data/concepts.json (capped at 300)

These files are committed to git by the GitHub Actions workflow and consumed
by Jekyll's Liquid templating engine on the next Pages deploy — giving the
blog a real-time window into the agent's internal state with zero infrastructure.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

_MAX_RUNS = 100
_MAX_CONCEPTS = 300

# Words that are too generic to be interesting concepts
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
        "being", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "shall", "it", "its", "this",
        "that", "these", "those", "i", "we", "they", "he", "she", "you",
        "not", "as", "if", "so", "yet", "nor", "both", "either", "about",
        "into", "through", "during", "before", "after", "above", "below",
        "between", "each", "which", "who", "what", "where", "when", "how",
        "all", "also", "just", "can", "new", "more", "than", "other", "their",
        "there", "here", "up", "out", "any", "our", "my", "your", "his", "her",
        "such", "same", "then", "now", "very", "even", "much", "many", "some",
        "most", "only", "use", "used", "using", "make", "made", "making",
        "show", "shows", "shown", "get", "gets", "got", "take", "takes",
        "taken", "see", "seen", "say", "said", "says", "one", "two", "three",
        "four", "five", "first", "last", "next", "like", "well", "paper",
        "work", "based", "model", "models", "learning", "trained", "data",
        "approach", "method", "result", "results", "performance", "different",
        "large", "small", "high", "low", "good", "better", "best", "while",
        "also", "however", "since", "although", "though", "because", "given",
        "where", "thus", "hence", "therefore", "note", "known", "called",
        "used", "show", "shown", "find", "found", "able", "need", "needs",
        "needed", "include", "includes", "including", "provide", "provides",
        "provided", "both", "each", "those", "these", "type", "types", "ways",
    }
)


def _extract_keywords(texts: list[str], top_n: int = 20) -> list[str]:
    """
    Extract the most distinctive technical keywords from a list of texts.

    Prioritises longer words (more likely to be technical terms) and
    filters out stop-words and single-character tokens.
    """
    combined = " ".join(texts)
    # Match words of 4+ chars; this catches most technical terms
    raw_words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", combined)
    words = [w.lower() for w in raw_words if w.lower() not in _STOP_WORDS]
    counts = Counter(words)
    return [w for w, _ in counts.most_common(top_n)]


def record_run(
    *,
    data_dir: Path,
    timestamp_utc: str,
    pages_attempted: int,
    pages_succeeded: int,
    post_written: bool,
    post_slug: str | None,
) -> None:
    """
    Append a run record to _data/runs.json, keeping the most recent _MAX_RUNS.

    Entry shape:
        {
            "timestamp":       ISO-8601 UTC string,
            "pages_attempted": int,
            "pages_succeeded": int,
            "success_rate":    float 0–1,
            "post_written":    bool,
            "post_slug":       str | null
        }
    """
    path = data_dir / "runs.json"
    runs: list[dict[str, Any]] = []
    if path.exists():
        try:
            runs = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(runs, list):
                runs = []
        except Exception:
            runs = []

    entry: dict[str, Any] = {
        "timestamp": timestamp_utc,
        "pages_attempted": pages_attempted,
        "pages_succeeded": pages_succeeded,
        "success_rate": round(pages_succeeded / max(pages_attempted, 1), 2),
        "post_written": post_written,
        "post_slug": post_slug,
    }
    runs.insert(0, entry)
    runs = runs[:_MAX_RUNS]

    data_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(runs, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def update_concepts(
    *,
    data_dir: Path,
    notes_texts: list[str],
    post_slug: str | None,
    today: str,
) -> None:
    """
    Extract keywords from a set of article texts and accumulate them into
    _data/concepts.json.

    Concept entry shape:
        {
            "count":      int,           # total times seen across all runs
            "first_seen": "YYYY-MM-DD",  # date of first encounter
            "last_seen":  "YYYY-MM-DD",  # date of most recent encounter
            "posts":      [slug, ...]    # last 10 post slugs where it appeared
        }
    """
    path = data_dir / "concepts.json"
    concepts: dict[str, Any] = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                concepts = raw
        except Exception:
            concepts = {}

    keywords = _extract_keywords(notes_texts, top_n=20)
    for kw in keywords:
        if kw not in concepts:
            concepts[kw] = {
                "count": 0,
                "first_seen": today,
                "last_seen": today,
                "posts": [],
            }
        entry = concepts[kw]
        entry["count"] = entry.get("count", 0) + 1
        entry["last_seen"] = today
        posts_list: list[str] = entry.get("posts", [])
        if post_slug and post_slug not in posts_list:
            posts_list.append(post_slug)
            entry["posts"] = posts_list[-10:]  # cap at last 10

    # Trim to the most-seen concepts to prevent unbounded growth
    if len(concepts) > _MAX_CONCEPTS:
        concepts = dict(
            sorted(concepts.items(), key=lambda kv: -kv[1].get("count", 0))
            [:_MAX_CONCEPTS]
        )

    data_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(concepts, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
