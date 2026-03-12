---
layout: post
title: "GitHub Pages + Claude: A Simple Blogging Setup"
date: 2026-02-22 00:00:00 +0000
categories: blogging automation
---

GitHub Pages is a free, no-frills way to host a blog. Pair it with Jekyll and you get a static site that lives directly in your repo — no databases, no hosting fees, just Markdown files and a `git push`.

## Why GitHub Pages for Blogging

- Free hosting under `username.github.io`
- Posts are just Markdown files in `_posts/`
- Version-controlled content out of the box
- Works with themes, plugins, and custom domains

## Automating Posts with Claude

This is where it gets interesting. Instead of manually writing and committing each post, you can use the **Claude API** to generate content and push it straight to your blog.

A simple workflow looks like this:

1. Send a prompt to Claude describing the post you want
2. Receive the Markdown response
3. Write it to `_posts/YYYY-MM-DD-title.md`
4. Commit and push — GitHub Pages rebuilds automatically

```python
import anthropic, datetime, subprocess

client = anthropic.Anthropic()
today = datetime.date.today()

response = client.messages.create(
    model="claude-opus-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Write a short blog post about productivity tips."}]
)

content = response.content[0].text
filename = f"_posts/{today}-productivity-tips.md"

with open(filename, "w") as f:
    f.write(f"---\nlayout: post\ntitle: Productivity Tips\ndate: {today}\n---\n\n{content}")

subprocess.run(["git", "add", filename])
subprocess.run(["git", "commit", "-m", "Add new post via Claude"])
subprocess.run(["git", "push"])
```

That's it. Claude writes, Git ships, GitHub Pages publishes.

## What This Unlocks

You can schedule this as a cron job, trigger it from a Slack message, or hook it into any workflow you already have. The blog stays simple and static — Claude just handles the words.
