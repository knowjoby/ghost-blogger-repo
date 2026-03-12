# Blog Project Context

Jekyll blog at https://knowjoby.github.io/blog — personal AI news feed, fully automated.

## Structure
- Posts → `_posts/YYYY-MM-DD-slug.md`
- Theme: minima (classic skin), baseurl `/blog`
- Auto-deploy via GitHub Actions on push to `main`

---

## Automated AI News Pipeline

### Run it
```
/ai-news
```
That's it. No confirmation, no review. Search → score → write → commit → push.

### What it does
1. Reads `data/news_queue.json` for today's usage and pending queue
2. Runs 3 web searches for recent AI company news
3. Scores each story (0–100) on recency, company tier, topic importance, uniqueness
4. Adds new stories to the pending queue
5. Picks the top stories within today's post quota (max 2/day)
6. Writes 150–200 word posts with auto-assigned tags
7. Saves posts, updates queue, commits, pushes to GitHub

### Companies tracked
Anthropic, OpenAI, Microsoft, Google DeepMind, Meta, xAI, Mistral, Cohere, Apple, Amazon, Nvidia — and any others making AI news.

### Tag taxonomy
**Company**: `anthropic` `openai` `microsoft` `google` `meta` `xai` `mistral` `cohere` `apple` `amazon` `nvidia`
**Topic**: `release` `controversy` `product` `bug` `rumor` `funding` `partnership` `policy` `safety` `unverified` `drama` `benchmark` `agentic` `multimodal`

Rumors → always tagged `rumor` + `unverified`. Speculation flagged inline in the text.

### Queue file
`data/news_queue.json` — tracks pending articles (scored, waiting), posted articles, and daily token/post usage. Never delete this file.

### Check queue status
```
python scripts/queue_status.py
python scripts/queue_status.py posted
python scripts/queue_status.py pending
python scripts/queue_status.py clear-old  # remove items older than 14 days
```

---

## Post format
```yaml
---
layout: post
title: "Title"
date: YYYY-MM-DD HH:MM:SS +0000
categories: ai-news
tags: [company, topic, ...]
score: 82
---
```
