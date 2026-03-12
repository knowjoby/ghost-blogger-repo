You are running the fully automated AI news pipeline for this blog. No confirmation needed at any step — search, score, write, commit, push. All decisions are yours.

---

## Step 1 — Load the queue

Read `data/news_queue.json`. Extract:
- `config`: daily_post_limit, daily_token_budget, min_score_to_post
- Today's date (YYYY-MM-DD)
- `daily_usage[today]`: posts already published today, estimated tokens used
- `pending`: scored articles waiting to be posted
- `posted`: already-published articles (use for deduplication)

Calculate:
- **posts_remaining** = config.daily_post_limit − today's posts
- **tokens_remaining** = config.daily_token_budget − today's estimated_tokens

If posts_remaining ≤ 0: skip posting, still do searches to add to queue, then print status and stop.

---

## Step 2 — Fetch news via LLM pipeline

Run the news fetcher script using the Bash tool:

```bash
python scripts/fetch_news_llm.py
```

This uses **DuckDuckGo News** (free, no key) to pull live articles, then **Groq (Llama)** to filter down to AI-relevant results.

Output is a JSON array of `{"title": "...", "url": "..."}` objects — one entry per article.

For each result, record: title, URL. Use the title to infer publication and date where possible. Write a 1-sentence summary of what happened based on the title (the script returns only title + link).

---

## Step 3 — Score each story

Score each story 0–100 using these rules:

**Recency (0–25)**
- Published today: 25
- 1–2 days ago: 18
- 3–5 days ago: 12
- 6–7 days ago: 6
- Older: 2

**Company tier (0–25)**
- Anthropic, OpenAI, Google DeepMind, Microsoft: 25
- Meta, xAI, Apple, Amazon, Nvidia: 18
- Mistral, Cohere, Stability, Inflection, others: 10

**Topic importance (0–30)**
- Safety incident, AI harm, major controversy: 30
- Major model release (GPT-5, Claude 4, Gemini 2 level): 25
- Significant product launch or feature: 20
- Funding, partnership, acquisition: 15
- Rumor, leak, or unverified claim: 10
- Minor update or statement: 5

**Uniqueness (0–20)**
- No similar topic in `posted` in last 7 days: 20
- Same company, different topic: 10
- Same company AND same topic already posted this week: 0

**Disqualify** (set score to 0) if:
- The story is already in `pending` or `posted` (matched by URL or very similar title)
- Score would be < config.min_score_to_post after all factors

---

## Step 4 — Update the pending queue

Add all new stories (score > 0, not duplicates) to `pending` in `data/news_queue.json`. Keep `pending` sorted by score DESC. Remove any pending items older than 14 days.

Save the updated queue file.

---

## Step 5 — Select and write posts

Take the top `posts_remaining` items from `pending` that meet `min_score_to_post`.

For each selected item, write a post:

**Length**: 150–200 words. Hard cap. Tight and informative.

**Structure**:
- Open with the fact: what happened, who, when.
- 1–2 sentences on why it matters or what changes.
- 1 sentence on what to watch next (if relevant).
- `**Source:** [Publication](url)` on the last line.

**Tone**: Neutral, slightly analytical. No hype. If it's a rumor or unverified, say so clearly in the text ("reportedly", "according to unverified sources", etc.).

**Tags**: Assign from these lists — be accurate, not generous:
- Company: `anthropic` `openai` `microsoft` `google` `meta` `xai` `mistral` `cohere` `apple` `amazon` `nvidia`
- Topic: `release` `controversy` `product` `bug` `rumor` `funding` `partnership` `policy` `safety` `unverified` `drama` `benchmark` `agentic` `multimodal`

Rumors always get `rumor` + `unverified`. Controversy gets `controversy`. Confirmed releases get `release`. Use as many accurate tags as needed.

**Filename**: `_posts/YYYY-MM-DD-short-slug.md` (slug: 3–5 words, lowercase, hyphenated)

**Front matter**:
```
---
layout: post
title: "Title Here"
date: YYYY-MM-DD HH:MM:SS +0000
categories: ai-news
tags: [tag1, tag2, tag3]
score: 82
---
```

Save each post file. Then update `data/news_queue.json`:
- Move the item from `pending` → `posted` (add `file`, `posted_at` fields)
- Increment `daily_usage[today].posts`
- Add 15000 to `daily_usage[today].estimated_tokens`

---

## Step 6 — Commit and push

```bash
git add data/news_queue.json _posts/
git commit -m "ai-news: [post title(s) summary]"
git push origin main
```

No confirmation. Just run it.

---

## Step 7 — Print summary

After pushing, output a clean summary:

```
✓ Posted today (N/2):
  • [score] "Post Title" → _posts/filename.md

📋 Queue (top pending for tomorrow):
  • [score] "Title" — company | topic
  • [score] "Title" — company | topic

📊 Today's usage: ~Xk tokens | X posts
```

That's it. Done.
