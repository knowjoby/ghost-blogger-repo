## Developer Guide (Functional + Technical Handover)

This repository powers a Jekyll blog that automatically publishes short “AI news” posts. It was assembled via AI-assisted “vibecoding”, so this guide is intentionally explicit and maps **directly to what exists in the repo**.

**Last audit**: 2026-02-23 (repo `main` at commit `9746ff3` at time of writing). This document includes the newer “smart fetch”/filter/monitor scripts and workflow that are present in the repo.

---

### What this repo does

- **Builds a static blog** using Jekyll (theme: `minima`, classic skin), hosted on GitHub Pages at `https://knowjoby.github.io/blog`.
- **Generates AI news posts automatically** using one (or more) of these pipelines:
  - **RSS pipeline (Python)**: `scripts/generate_news.py` fetches RSS feeds, scores + dedupes items, writes minimal link-posts into `_posts/`, updates `data/news_queue.json`, and appends to `_data/run_log.json`.
  - **Agent pipeline (Claude command)**: `.claude/commands/ai-news.md` defines a fully-automated workflow that does web search, scores items, writes 150–200 word posts, updates queue, commits, and pushes.
- **Includes experimental “smart fetch / filter / monitor” building blocks**:
  - `scripts/smart_fetcher.py`, `scripts/smart_scheduler.py`, `scripts/check_new_content.py`, `scripts/ai_news_filter.py`, `scripts/breaking_news_monitor.py`
  - `.github/workflows/smart-news-fetch.yml` runs every 30 minutes.
  - **Important**: as currently committed, these “smart” scripts are scaffolding and contain placeholders/undefined methods that will fail if executed as-is. See the “Experimental smart fetch pipeline” section for details and risks.
- **Automates runs and deployments** via GitHub Actions workflows under `.github/workflows/`.

---

### Repo structure (important directories/files)

- **Jekyll site**
  - `_config.yml`: Jekyll config. Key settings include:
    - `baseurl: "/blog"` (local URL paths include `/blog`)
    - `theme: minima`
  - `_posts/`: All posts. Generated AI news posts are created here.
  - `_layouts/`, `_includes/`: Jekyll layout and include overrides/customizations.
  - `index.md`, `about.md`, `logs.md`: top-level pages.
- **Automation data**
  - `data/news_queue.json`: persistent queue + config + daily usage. **Never delete.**
  - `_data/run_log.json`: last ~50 runs of the RSS pipeline (used by monitoring).
- **Scripts**
  - `scripts/generate_news.py`: RSS-based AI news generator.
  - `scripts/queue_status.py`: CLI tool to inspect/clean the queue.
  - `scripts/run_ai_news.sh`: local LaunchAgent-friendly runner for Claude `/ai-news`.
  - `scripts/ai_news_filter.py`: alternative RSS filter/post generator (creates `_data/ai-news-<date>.yaml` and `_posts/<date>-ai-news-<n>.md`).
  - `scripts/check_new_content.py`: counts new posts since last build; used by `smart-news-fetch.yml` to decide whether to rebuild/deploy.
  - `scripts/smart_fetcher.py`: placeholder “smart” fetch framework for rate-limiting/refresh scheduling per source (currently incomplete).
  - `scripts/smart_scheduler.py`: refresh schedule constants (data only).
  - `scripts/breaking_news_monitor.py`: breaking-news detection + alert hooks (currently not wired into any workflow).
- **Claude command (agent flow)**
  - `.claude/commands/ai-news.md`: specification for the `/ai-news` command.
- **GitHub Actions**
  - `.github/workflows/daily-news.yml`: runs RSS pipeline daily + commits/pushes changes.
  - `.github/workflows/monitor.yml`: verifies daily run happened; retriggers if missing.
  - `.github/workflows/jekyll.yml`: builds and deploys the Jekyll site to GitHub Pages.
  - `.github/workflows/smart-news-fetch.yml`: high-frequency (every 30 min) “smart fetch” workflow (currently inconsistent with the repo’s Pages deployment approach; see below).

---

## Functional Overview (What users “get”)

### AI news posts

AI news posts are regular Jekyll posts with:

- `categories: ai-news`
- `tags`: company and topic tags (from keyword rules)
- `score`: a numeric importance score

Depending on pipeline:

- **RSS (Python)** posts are minimal link posts with:
  - Front matter includes `link`, `source`, `original_date`.
  - Body contains a single “Read on …” link.
- **Claude `/ai-news`** posts are 150–200 word summaries and end with a source line.

### Queue behavior (pending vs posted)

The system maintains a queue of candidate stories:

- **`pending`**: scored items that were found but not yet posted (kept sorted by score).
- **`posted`**: history of stories already converted into `_posts/` files.

The queue is used for:

- Deduplication (avoid reposting the same story)
- Posting caps (max posts per day)
- Carry-over of high quality items for tomorrow

---

## Technical Guide

### 1) Local development (Jekyll site)

This is a normal Jekyll site with `minima` theme.

Typical local run (exact Ruby version/tooling may vary by machine):

```bash
bundle install
bundle exec jekyll serve
```

Because `baseurl` is `/blog`, the local site will typically be at:

- `http://localhost:4000/blog`

---

### 2) RSS pipeline (Python): `scripts/generate_news.py`

#### Purpose

Fully automated RSS-based AI news link-post generator:

- Pulls RSS entries from a curated list of sources
- Filters to recent and AI-relevant items
- Auto-tags by company/topic keyword rules
- Scores each story (0–100)
- De-duplicates cross-source coverage
- Writes new posts to `_posts/`
- Updates queue state in `data/news_queue.json`
- Appends a run record to `_data/run_log.json`

#### Runtime requirements

- Python 3
- Dependency: `feedparser`

```bash
pip install feedparser
python scripts/generate_news.py
```

**Newer dependency note (current repo state):** `scripts/generate_news.py` now tries to import helper logic from `scripts/ai_news_filter.py` (`extract_companies_mentioned`) to enhance company detection. That helper file imports `yaml` (PyYAML). If you keep this integration, the RSS pipeline’s runtime dependencies become:

- `feedparser`
- `pyyaml`

Also, the import is written as `from scripts.ai_news_filter import ...`, which requires Python to treat `scripts/` as an importable package/module path (it is not a package by default unless you add `scripts/__init__.py` or adjust `PYTHONPATH`). If this is not corrected, the daily RSS workflow (`daily-news.yml`) will fail at import time.

#### Inputs / outputs

- **Reads**
  - `data/news_queue.json`
  - RSS feed URLs (network)
- **Writes**
  - New Markdown post files under `_posts/`
  - Updated `data/news_queue.json`
  - Updated `_data/run_log.json`

#### Scoring & filtering behavior (exact)

The script assigns:

- **Company tags** via `COMPANY_KEYWORDS`
- **Topic tags** via `TOPIC_KEYWORDS`
  - If `rumor` is detected, it automatically adds `unverified`.

It filters candidates by:

- Must have `title` and `link`
- Must not already exist in `posted` or `pending` by URL
- Must be within last **7 days**
- Must be AI-relevant:
  - Either mentions a known company, or contains a strong topic (`release`, `safety`, `policy`, `agentic`), or contains generic AI phrases (`llm`, `generative ai`, etc.)
- Must have score ≥ 10 (hard-coded pre-threshold)

Score components:

- **Recency (0–25)** based on age in days
- **Company tier (0–25)**:
  - Tier 1: `anthropic`, `openai`, `google`, `microsoft`
  - Tier 2: `meta`, `xai`, `apple`, `amazon`, `nvidia`
- **Topic importance (0–30)** using a weights table (e.g., `safety` highest)
- **Uniqueness (0–20)** penalized if similar to existing titles

Cross-source dedupe:

- Uses `titles_are_similar()` with a word-overlap ratio threshold (default 0.45).
- Keeps the highest scored item when duplicates are detected.

Posting limits:

- Daily total is enforced via `data/news_queue.json` `config.daily_post_limit` and `daily_usage[today].posts`.
- A per-company limit is also applied:
  - `PER_COMPANY_LIMIT = 2` posts per company per run/day.

Post format written by RSS pipeline:

- Filename: `_posts/YYYY-MM-DD-<slug>.md`
- Front matter includes:
  - `layout: post`
  - `categories: ai-news`
  - `tags: [...]`
  - `score: <int>`
  - `link: <url>`
  - `source: <source name>`
  - `original_date: <YYYY-MM-DD>`
- Body contains:
  - `[Read on <source>](<url>)`

Pending queue behavior:

- If there are remaining high-quality candidates after posting:
  - Up to 10 are added to `pending` if score ≥ 40
- `pending` is sorted by score descending
- Any pending items older than 14 days are dropped

Run log behavior:

- Appends an entry to `_data/run_log.json`
- Keeps only last 50 runs
- Sets `triggered_by` based on `GITHUB_EVENT_NAME`
- Records per-feed stats (entries and errors)

---

### 3) Queue utilities: `scripts/queue_status.py`

#### Purpose

Operational CLI tool to view or clean the AI news queue.

#### Commands

```bash
python scripts/queue_status.py
python scripts/queue_status.py status
python scripts/queue_status.py posted
python scripts/queue_status.py pending
python scripts/queue_status.py clear-old
python scripts/queue_status.py clear-old 21
```

What each does:

- **`status`** (default)
  - Prints today’s post usage vs limit, token usage vs budget, min score threshold
  - Shows top 5 pending items
  - Shows 5 most recently posted items
- **`posted`**
  - Prints all posted items (score, tags, file path)
- **`pending`**
  - Prints full pending queue (score, tags, source URL, added date)
- **`clear-old [days]`**
  - Removes pending items older than N days (default 14) and saves the queue

---

### 4) Claude agent pipeline: `.claude/commands/ai-news.md`

This file defines the instructions for the Claude Code CLI command `/ai-news`.

Key differences vs RSS pipeline:

- Uses **web search** (3 searches) rather than RSS feeds
- Writes full 150–200 word posts (not just a link)
- Updates `daily_usage[today].estimated_tokens` by +15000 per post
- Performs `git add`, `git commit`, `git push` automatically per spec

Important notes:

- Rumors must be labeled and get `rumor` + `unverified` tags.
- Posts must end with `**Source:** [Publication](url)`.

If your team standardizes on the RSS pipeline, treat this as optional/legacy; if you rely on it, maintain it like production code because it can commit and push.

---

### 5) Local scheduled runner: `scripts/run_ai_news.sh`

Purpose:

- Bash wrapper intended for macOS LaunchAgent scheduling.
- Runs the Claude CLI command `/ai-news` non-interactively and logs output.

Behavior:

- Hard-coded paths:
  - `BLOG_DIR="/Users/jobyjohn/github-blog"`
  - `CLAUDE_BIN="/Users/jobyjohn/.local/bin/claude"`
  - Logs to `"$BLOG_DIR/logs/ai-news.log"`
- Runs:
  - `claude --dangerously-skip-permissions -p "/ai-news"`

Operational risks / things to fix for team use:

- Paths should be configurable (env vars) rather than hard-coded per-user.
- `--dangerously-skip-permissions` means no interactive safety checks; ensure the `/ai-news` spec is trustworthy.

---

### 6) Experimental smart fetch pipeline (high frequency)

This repo contains an additional workflow and helper scripts intended to support more frequent fetching and conditional deploys.

#### Workflow: `.github/workflows/smart-news-fetch.yml`

- **Schedule**: every 30 minutes (`*/30 * * * *`) + manual dispatch.
- **Steps (as written)**:
  1. Checkout code
  2. Setup Python 3.9
  3. `pip install feedparser pyyaml requests`
  4. Run `python scripts/smart_fetcher.py`
  5. Run `python scripts/check_new_content.py` and capture output as `NEW_COUNT`
  6. If `NEW_COUNT > 0` (or manual dispatch):
     - Run `bundle install` and `bundle exec jekyll build`
     - Deploy using `peaceiris/actions-gh-pages@v3` from `./_site`

#### Script: `scripts/smart_fetcher.py` (current state: incomplete / will fail)

This file defines a `SmartNewsFetcher` class intended to:

- Track last fetch times per source in `data/last_fetch_times.json`
- Fetch only sources that are “due” based on per-source-type intervals

However, as committed:

- `self.schedules` contains placeholders like `sources: [...]` (a list containing an `Ellipsis`), not real source dicts.
- It calls `self.update_last_run(...)` but **no such method exists**.
- `fetch_source()` is `pass`.

Result: running `python scripts/smart_fetcher.py` will error if execution reaches `fetch_due_sources()`, and it does not produce posts or update `data/news_queue.json`.

#### Script: `scripts/check_new_content.py` (build gating)

- Tracks build state in `data/last_build_state.json`.
- Counts “new posts” as `_posts/*.md` files that weren’t present in the last saved state.
- **Exit codes**:
  - Exits **0** if new files exist.
  - Exits **1** if no new files exist.

In GitHub Actions, a non-zero exit usually fails the step. The workflow currently runs:

- `NEW_COUNT=$(python scripts/check_new_content.py)`

Because the script exits 1 when there are no new posts, this step will typically fail on “no-op” runs unless the workflow is configured to tolerate non-zero exit codes (it is not currently).

#### Deployment inconsistency (important)

This workflow deploys using `peaceiris/actions-gh-pages@v3`, while the repo’s primary deployment (`.github/workflows/jekyll.yml`) deploys via GitHub Pages’ official `actions/deploy-pages@v4`.

The dev team should decide one deployment strategy and remove/disable the other to avoid conflicting publishes.

---

### 7) Alternate filter/post generator: `scripts/ai_news_filter.py` (not the same as `generate_news.py`)

This script is a separate RSS-based fetch + filter pipeline with different outputs:

- Uses an expanded `SOURCES` list (Substack newsletters, company blogs, AI category feeds)
- Uses `COMPANY_KEYWORDS` with additional entries (includes `deepseek`)
- Filters items by “company mention” using occurrence counts and regex checks
- Builds a list of post dicts with:
  - `title`, `link`, `date`, `source`, `summary`, `companies` (dict with scores), `primary_company`, `relevance_score`

Outputs (as written):

- Writes up to **20** posts as:
  - `_posts/<today>-ai-news-<i>.md`
  - Front matter includes `source`, `companies`, `primary`, `link`
  - Body contains a summary snippet and a “Read full article” link
- Writes a YAML file:
  - `_data/ai-news-<today>.yaml` containing up to 50 items

Known gaps in the script (as committed):

- References `update_source_health(...)` but does not define it.
- Uses PyYAML (`import yaml`), so it requires `pyyaml` at runtime.
- It is not referenced directly by `daily-news.yml`, but `generate_news.py` currently imports `extract_companies_mentioned` from this file.

---

### 8) Breaking-news monitor: `scripts/breaking_news_monitor.py`

This file defines a `BreakingNewsMonitor` class intended to:

- Track already-alerted breaking links in `data/breaking_news_cache.json`
- Identify “breaking” items based on:
  - Mentioning a primary company (`openai`, `anthropic`, `google`, `deepseek`)
  - Title containing breaking keywords (e.g., `GPT-5`, `Claude 4`, `Gemini Ultra`, `acquisition`, etc.)
  - Or a high `relevance_score` (> 5)
- Provide alert hooks:
  - `send_email_alert()` (currently stub/prints)
  - `post_to_social()` (currently stub/prints)

As committed:

- There is no `__main__` entry point wiring it into a workflow.
- It imports `smtplib` and `requests` but does not implement real alert sending.

Treat this as scaffolding unless/until it is integrated.

---

## Data formats (must remain stable)

### `data/news_queue.json` (queue + config)

This file is treated as persistent state. It must always contain these top-level keys:

- `config`
- `daily_usage`
- `pending`
- `posted`

Expected `config` keys (used by scripts/workflows):

- `daily_post_limit` (int)
- `daily_token_budget` (int)
- `min_score_to_post` (int)
- `max_words_per_post` (int) (used by agent spec; RSS generator doesn’t enforce word count)

`daily_usage` is keyed by date string `YYYY-MM-DD`:

- `posts` (int)
- `estimated_tokens` (int)

`pending` item fields used by scripts:

- `id` (string)
- `title` (string)
- `source_url` (string)
- `companies` (array of strings)
- `topics` (array of strings)
- `score` (int)
- `added_at` (YYYY-MM-DD)
- `source` (optional; used when promoting pending → post in RSS pipeline)

`posted` item fields used by scripts:

- same as pending plus:
  - `file` (e.g., `_posts/2026-02-23-some-slug.md`)
  - `posted_at` (YYYY-MM-DD)

### `_data/run_log.json` (RSS pipeline run history)

This is a JSON array. Each entry includes:

- `ran_at` (string, IST timestamp)
- `triggered_by` (string)
- `candidates_found` (int)
- `posts_created` (int)
- `queued` (int)
- `feeds` (object with per-source stats)
- `posts` (array of title/file/score/tags for posts created in that run)

The RSS generator truncates this file to the last 50 runs.

---

## GitHub Actions (automation)

### Daily news generation: `.github/workflows/daily-news.yml`

- Runs on a daily schedule (cron) and on manual dispatch.
- Sets up Python and installs `feedparser`.
- Runs `python scripts/generate_news.py`.
- Commits and pushes any resulting changes (posts + queue + run log).

### Monitoring + retry: `.github/workflows/monitor.yml`

- Runs after the scheduled daily job at multiple offsets (e.g., 30/90/180 minutes).
- Checks `_data/run_log.json` for a run recorded “today”.
- If missing, triggers the `daily-news.yml` workflow again using `gh workflow run ...`.

### Build and deploy: `.github/workflows/jekyll.yml`

- Runs on push to `main`, on a schedule, and on manual dispatch.
- Builds the Jekyll site and deploys to GitHub Pages.

### Smart high-frequency fetch (experimental): `.github/workflows/smart-news-fetch.yml`

- Runs every 30 minutes.
- Installs Python deps and runs `scripts/smart_fetcher.py`.
- Uses `scripts/check_new_content.py` to decide whether to build/deploy.
- Deploys with `peaceiris/actions-gh-pages@v3` (different deployment model than `jekyll.yml`).

---

## Operational runbook

### Run RSS pipeline locally

```bash
pip install feedparser
python scripts/generate_news.py
python scripts/queue_status.py status
```

### Check queue health

```bash
python scripts/queue_status.py status
python scripts/queue_status.py pending
python scripts/queue_status.py posted
```

### Clear old pending items

```bash
python scripts/queue_status.py clear-old
python scripts/queue_status.py clear-old 21
```

---

## Common failure modes / troubleshooting

### “No new AI news items found.”

Causes:

- RSS feeds changed format or are down
- Candidate filters too strict
- Daily post limit already reached

Debug actions:

- Check `feed_stats` recorded in `_data/run_log.json` (entries and errors)
- Temporarily add more sources to `RSS_FEEDS`
- Lower `config.min_score_to_post` in `data/news_queue.json`

### Duplicate or near-duplicate posts

Causes:

- `titles_are_similar()` threshold too low/high for your sources
- Different outlets use different wording for same event

Mitigations:

- Tune `titles_are_similar()` threshold
- Improve uniqueness rules in `score_item()`

### Daily pipeline ran but didn’t post

Causes:

- `posts_remaining <= 0` (daily limit reached)
- Candidates all below `min_score_to_post`
- Per-company cap prevented posting

Debug actions:

- Check `data/news_queue.json` `daily_usage[today]`
- Check pending queue top scores

---

## Extension points (where to change behavior safely)

- Add/remove RSS sources: edit `RSS_FEEDS` in `scripts/generate_news.py`
- Improve tagging: adjust `COMPANY_KEYWORDS` / `TOPIC_KEYWORDS`
- Scoring: modify `score_item()` weights and thresholds
- Deduplication: modify `titles_are_similar()` logic/threshold
- Posting caps:
  - Global: `config.daily_post_limit`
  - Per-company: `PER_COMPANY_LIMIT` in `generate_news.py`
- Post formatting:
  - RSS posts: modify the `content` template in `generate_news.py`
  - Agent posts: modify `.claude/commands/ai-news.md`
- Automation cadence: adjust cron schedules in `.github/workflows/*.yml`

