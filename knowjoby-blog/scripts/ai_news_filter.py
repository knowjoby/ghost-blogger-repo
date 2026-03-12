#!/usr/bin/env python3
"""
AI News Filter - Utility functions for filtering and scoring AI news.
This module now imports all configuration from config.py.
"""

import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Set
from difflib import SequenceMatcher

# Import shared configuration
from scripts.config import (
    match_keywords,
    detect_companies,
    detect_topics,
    COMPANY_KEYWORDS,
    TOPIC_KEYWORDS
)


def filter_relevant_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter a list of articles to those relevant to AI/ML.
    
    Args:
        articles: List of article dicts with 'title' and 'description'
        
    Returns:
        Filtered list with added 'companies' and 'topics' fields
    """
    filtered = []
    
    for article in articles:
        title = article.get('title', '')
        description = article.get('description', '')
        combined = f"{title} {description}"
        
        # Detect companies and topics
        companies = detect_companies(combined)
        topics = detect_topics(combined)
        
        # Keep if any matches found
        if companies or topics:
            article['companies'] = companies
            article['topics'] = topics
            filtered.append(article)
    
    return filtered


def calculate_relevance_score(article: Dict[str, Any]) -> int:
    """
    Calculate a relevance score for an article.
    Simpler scoring than generate_news.py, used for quick filtering.
    
    Args:
        article: Article dict with 'companies' and 'topics'
        
    Returns:
        Score from 0-100
    """
    score = 0
    companies = article.get('companies', [])
    topics = article.get('topics', [])
    title = article.get('title', '').lower()
    
    # Company weights
    tier1_companies = [
        "openai", "anthropic", "google", "microsoft", "meta", "xai",
        "amazon", "apple", "nvidia"
    ]
    
    for company in companies:
        if company in tier1_companies:
            score += 30
            # Bonus if company in title
            if company in title:
                score += 15
        else:
            score += 15
    
    # Topic weights
    for topic in topics:
        score += 10
        if topic in title:
            score += 5
    
    return min(100, score)


def update_source_health(source_name: str, success: bool, health_data: Dict) -> Dict:
    """
    Update source health tracking data.
    
    Args:
        source_name: Name of the RSS source
        success: Whether fetch was successful
        health_data: Current health data dict
        
    Returns:
        Updated health data
    """
    if source_name not in health_data:
        health_data[source_name] = {
            'last_ok': None,
            'consecutive_failures': 0,
            'total_entries': 0
        }
    
    if success:
        health_data[source_name]['last_ok'] = datetime.now().isoformat()
        health_data[source_name]['consecutive_failures'] = 0
    else:
        health_data[source_name]['consecutive_failures'] += 1
    
    return health_data


def titles_are_similar(title1: str, title2: str, threshold: float = 0.8) -> bool:
    """
    Check if two titles are similar enough to be duplicates.
    Exported for use by other modules.
    """
    t1 = title1.lower().strip()
    t2 = title2.lower().strip()
    
    if t1 == t2:
        return True
    
    if len(t1) > len(t2):
        long, short = t1, t2
    else:
        long, short = t2, t1
    
    if short in long and len(short) > 15:
        return True
    
    ratio = SequenceMatcher(None, t1, t2).ratio()
    return ratio > threshold


if __name__ == "__main__":
    # Simple test
    test_articles = [
        {"title": "OpenAI releases GPT-4 with improved reasoning", "description": "..."},
        {"title": "Apple announces new ML framework for iOS", "description": "..."},
        {"title": "Random tech news about databases", "description": "..."}
    ]
    
    filtered = filter_relevant_articles(test_articles)
    for article in filtered:
        score = calculate_relevance_score(article)
        print(f"{article['title']} -> Score: {score}, Companies: {article.get('companies', [])}")
