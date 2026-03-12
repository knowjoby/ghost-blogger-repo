#!/usr/bin/env python3
"""
Fetch AI news titles and links using DuckDuckGo search + Groq LLM filtering.

Usage:
    python scripts/fetch_news_llm.py
    python scripts/fetch_news_llm.py --no-groq   # skip LLM filter, return all results

Output: JSON array of {"title": ..., "url": ...} to stdout
Logs:   progress messages to stderr
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"  # fast, free-tier friendly

SEARCH_QUERIES = [
    "AI model release news March 2026",
    "OpenAI OR Anthropic OR Google DeepMind OR xAI news 2026",
    "AI safety controversy announcement funding 2026",
]

MAX_RESULTS_PER_QUERY = 15   # DuckDuckGo results per query
TIMELIMIT = "w"              # past week; use "d" for today only


# ---------------------------------------------------------------------------
# Step 1: Fetch raw titles + links via DuckDuckGo News (no API key required)
# ---------------------------------------------------------------------------

def fetch_news_ddg() -> list:
    """Return a deduplicated list of {title, url, source, date, snippet} dicts."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        print("ERROR: duckduckgo-search not installed. Run: pip install duckduckgo-search", file=sys.stderr)
        sys.exit(1)

    articles = []
    seen_urls: set = set()

    with DDGS() as ddgs:
        for query in SEARCH_QUERIES:
            try:
                results = list(ddgs.news(keywords=query, max_results=MAX_RESULTS_PER_QUERY, timelimit=TIMELIMIT))
                for r in results:
                    url = r.get("url", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        articles.append({
                            "title": r.get("title", "").strip(),
                            "url": url,
                            "source": r.get("source", ""),
                            "date": r.get("date", ""),
                            "snippet": (r.get("body", "") or "")[:200],
                        })
            except Exception as e:
                print(f"DDG search error for query '{query}': {e}", file=sys.stderr)

    print(f"[fetch] Fetched {len(articles)} raw articles from DuckDuckGo", file=sys.stderr)
    return articles


# ---------------------------------------------------------------------------
# Step 2: Filter with Groq LLM — keep only AI-relevant, return title + url
# ---------------------------------------------------------------------------

def filter_with_groq(articles: list) -> list:
    """
    Send article titles to Groq (Llama) and get back only the AI-relevant ones.
    Returns list of {"title": ..., "url": ...} dicts.
    """
    if not GROQ_API_KEY:
        print("[groq] No GROQ_API_KEY found — skipping LLM filter, returning all results", file=sys.stderr)
        return [{"title": a["title"], "url": a["url"]} for a in articles]

    try:
        from groq import Groq
    except ImportError:
        print("ERROR: groq not installed. Run: pip install groq", file=sys.stderr)
        return [{"title": a["title"], "url": a["url"]} for a in articles]

    client = Groq(api_key=GROQ_API_KEY)

    numbered = "\n".join(
        f"{i + 1}. {a['title']} | {a['url']}"
        for i, a in enumerate(articles)
    )

    prompt = f"""You are a filter for an AI news blog. Review the list below and return ONLY articles that are directly about:
- AI model releases or updates
- AI company announcements (OpenAI, Anthropic, Google DeepMind, Microsoft, Meta, xAI, Nvidia, Apple, Amazon, Mistral, Cohere, etc.)
- AI safety, alignment, or policy
- AI products, benchmarks, or research
- AI funding, acquisitions, or partnerships
- AI controversy, drama, or incidents

Exclude: general tech news, hardware unrelated to AI, unrelated topics.

Articles:
{numbered}

Respond with a JSON array only — no explanation, no markdown. Each item: {{"title": "...", "url": "..."}}
"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=3000,
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()

        filtered = json.loads(raw)
        print(f"[groq] Filtered to {len(filtered)} AI-relevant articles", file=sys.stderr)
        return filtered

    except Exception as e:
        print(f"[groq] Filtering error: {e} — falling back to unfiltered results", file=sys.stderr)
        return [{"title": a["title"], "url": a["url"]} for a in articles]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    use_groq = "--no-groq" not in sys.argv

    articles = fetch_news_ddg()
    if not articles:
        print("[]")
        return

    if use_groq:
        result = filter_with_groq(articles)
    else:
        result = [{"title": a["title"], "url": a["url"]} for a in articles]

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
