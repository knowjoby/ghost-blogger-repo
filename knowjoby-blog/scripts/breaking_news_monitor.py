#!/usr/bin/env python3
"""
Breaking News Monitor - Detects and logs high-importance AI news.
"""

import sys
from pathlib import Path
# Add repo root to path for imports when running script directly
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime
from typing import List, Dict, Any, Optional

# Import shared configuration
from scripts.config import match_keywords

# Keywords that indicate breaking news
BREAKING_KEYWORDS = [
    # Major announcements
    "releases", "announces", "launches", "unveils", "introduces",
    "breakthrough", "milestone", "revolutionary",
    
    # Model releases (current generation)
    "gpt-4o", "gpt4o", "claude 3.7", "claude 4", "gemini 2.0",
    "llama 3.3", "llama 4", "deepseek v3", "o3", "sora",
    
    # Major events
    "acquisition", "merger", "partnership", "investment",
    "ceo", "leadership", "restructuring",
    
    # Controversial/important topics
    "safety", "alignment", "regulation", "ban", "investigation",
    "lawsuit", "copyright", "scandal"
]

BREAKING_SCORE_THRESHOLD = 80  # Minimum score to consider breaking

BASE_DIR = Path(__file__).parent.parent
RUN_LOG_FILE = BASE_DIR / "_data" / "run_log.json"


def log_breaking_news(post: Dict[str, Any]) -> None:
    """
    Log a breaking news item to the run log.
    
    Args:
        post: Post dictionary with title, companies, score, etc.
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "type": "breaking_news",
        "title": post.get("title", ""),
        "score": post.get("score", 0),
        "companies": post.get("companies", []),
        "filename": post.get("filename", "")
    }
    
    # Append to run log
    log_data = []
    if RUN_LOG_FILE.exists():
        with open(RUN_LOG_FILE, 'r') as f:
            try:
                log_data = json.load(f)
            except json.JSONDecodeError:
                log_data = []
    
    log_data.append(log_entry)
    
    # Keep only last 200 entries
    if len(log_data) > 200:
        log_data = log_data[-200:]
    
    with open(RUN_LOG_FILE, 'w') as f:
        json.dump(log_data, f, indent=2)
    
    print(f"  🚨 BREAKING: {post.get('title', '')[:80]}...")


def check_for_breaking_news(posts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Check a list of posts for breaking news candidates.
    
    Args:
        posts: List of post dictionaries (from generate_news.py output)
        
    Returns:
        List of posts that qualify as breaking news
    """
    breaking_posts = []
    
    for post in posts:
        # Skip if no score
        score = post.get('score', 0)
        if score < BREAKING_SCORE_THRESHOLD:
            continue
        
        # Check title for breaking keywords
        title = post.get('title', '').lower()
        is_breaking = match_keywords(title, BREAKING_KEYWORDS)
        
        if is_breaking:
            log_breaking_news(post)
            breaking_posts.append(post)
    
    return breaking_posts


if __name__ == "__main__":
    # Test with sample data
    test_posts = [
        {
            'title': 'OpenAI announces GPT-4o with real-time voice',
            'score': 95,
            'companies': ['openai'],
            'filename': '2026-02-28-openai-announces.md'
        },
        {
            'title': 'Minor update to API documentation',
            'score': 45,
            'companies': ['openai'],
            'filename': '2026-02-28-api-update.md'
        }
    ]
    
    breaking = check_for_breaking_news(test_posts)
    print(f"Found {len(breaking)} breaking news items")
