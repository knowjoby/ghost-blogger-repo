# Handover (Blog Ops + Code Map)

This repository powers `https://knowjoby.github.io/blog` — an automated AI news feed (Jekyll + GitHub Actions).

The site is designed to be “daily-drivable”:

- **Homepage** is the briefing + feed (what you read).
- **Status** shows automation health (what you check when things look stale).
- **Archives** lets you search both **Published** and **Queue** (what you use to debug coverage and dedupe).

Date of last major pass: **2026-03-12**.

---

## What’s running in production

### Automation workflows

Workflows live in `.github/workflows/`:

- `smart-news-fetch.yml`
  - Runs **every 30 minutes**
  - Runs `python scripts/generate_news.py`
  - Commits and pushes any changes (posts + queue + logs + public queue)
- `daily-news.yml`
  - Runs daily (backup cadence)
  - Same generator + commit behavior
- `jekyll.yml`
  - Deploys GitHub Pages on push to `main`

### The generator (single source of truth)

Main script: `scripts/generate_news.py`

What it does:

1. Loads state from `data/news_queue.json` (private state: posted + pending + usage).
2. Fetches candidates (DDG News first; RSS fallback if DDG is blocked on runners).
3. Filters + scores items using keyword rules in `scripts/config.py`.
4. Writes new posts into `_posts/` up to `config.daily_post_limit`.
5. Updates queue state in `data/news_queue.json`.
6. Appends run info to `_data/run_log.json` (for Status page).
7. Publishes a **sanitized, deduped** queue snapshot to `_data/news_queue_public.json` (for UI).

Important: GitHub Pages/Jekyll can read `_data/*.json`, but not arbitrary `/data` JSON. That’s why the public queue file exists.

---

## Data files (what they mean)

- `data/news_queue.json`
  - **Private** state for the automation.
  - Contains `pending` (not yet posted), `posted` (already posted), and `daily_usage`.
- `_data/run_log.json`
  - **Public** operational history (last ~50 runs).
  - Used by `/logs/` (Status).
- `_data/news_queue_public.json`
  - **Public** queue snapshot.
  - Contains only pending items, deduped vs posted, limited to top ~200.
  - Used by homepage Queue panel and Archives “Queue” tab.

---

## UI pages (current UX)

### `/` (Homepage)

Layout: `_layouts/home.html`

Contains:

- “Briefing” block (top items from recent window)
- “Queue (next up)” collapsible section (from `_data/news_queue_public.json`)
- Main feed grouped by date, with tag filtering, “new since last visit”, and “show older”

Note: scoring still exists internally, but the UI is intentionally **not score-first**. The homepage and archives are designed for chronological reading, with queue visibility for operators.

Notable knobs:

- `INITIAL_LIMIT` controls how many feed items show by default (currently higher than the original).

### `/logs/` (Status)

Source: `logs.md`

Shows:

- Latest run stats from `_data/run_log.json`
- Recent run history table

### `/archives/` (Archives)

Source: `archives.md`

Tabs:

- Published (Jekyll posts)
- Queue (from `_data/news_queue_public.json`)

Both support:

- search
- tag filtering

### `/about/`

Source: `about.md`

Contains short explanation + embedded RSS fallback source list (from `_data/rss_sources.json`).

### `/changelog/`

Source: `changelog.md`

Also linked globally via `_includes/footer.html`.

### `/now/`

Source: `now.md`

This is an alias/redirect to the homepage (kept for old links).

---

## RSS fallback sources

File: `_data/rss_sources.json`

Used by:

- `scripts/generate_news.py` RSS fallback
- `about.md` display

Update this list if you want to change the reliable fallback behavior.

---

## Running locally

### Generator

```bash
python3 -m pip install -r requirements.txt
python3 scripts/generate_news.py --dry-run
python3 scripts/generate_news.py
```

### Jekyll site

Bundler is pinned to install into `vendor/bundle` locally in this repo:

```bash
bundle install --path vendor/bundle
bundle exec jekyll build
bundle exec jekyll serve
```

---

## Deployment model (mental model)

1. Generator commits content to `main`.
2. GitHub Pages deploy workflow builds the static site.
3. UI reads:
   - posts from `_posts/`
   - run log from `_data/run_log.json`
   - queue snapshot from `_data/news_queue_public.json`

If the homepage looks stale:

- Check `/logs/` first (run history).
- If runs are happening but no new posts: it may be “no candidates” (normal), or DDG/RSS availability changed.

---

## Known sharp edges / notes

- **Jekyll data parsing:** Some setups can choke on JSON with escaped Unicode surrogate pairs. Public queue JSON is written with `ensure_ascii=False` to avoid that.
- **Queue size:** `data/news_queue.json` can grow. Public queue is capped.
- **Title encoding:** Generator unescapes HTML entities from sources; templates also include a small unescape for already-posted titles.

---

## Next high-leverage improvements (optional)

- Add a lightweight “Queue → Publish” policy (e.g., publish from queue when no fresh candidates).
- Add a `/health/` page that just shows “last post age” + “last run age” in one line.
- Add per-source stats (RSS/ DDG) to the Status page if you want deeper ops visibility.
