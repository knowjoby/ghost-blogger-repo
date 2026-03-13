# Ghost Blogger

> A GitHub-native autonomous agent that reads public AI/ML sources and publishes daily reflective notes — no external APIs, no keys, no manual effort.

[![Ghost Blogger](https://github.com/knowjoby/ghost-blogger-repo/actions/workflows/ghost_blogger.yml/badge.svg)](https://github.com/knowjoby/ghost-blogger-repo/actions/workflows/ghost_blogger.yml)
[![Pages Deploy](https://github.com/knowjoby/ghost-blogger-repo/actions/workflows/pages.yml/badge.svg)](https://github.com/knowjoby/ghost-blogger-repo/actions/workflows/pages.yml)

**Live blog →** [knowjoby.github.io/ghost-blogger-repo](https://knowjoby.github.io/ghost-blogger-repo/)

---

## What it does

Every 15 minutes, a GitHub Actions workflow wakes up `gh-ghost` — a polite web-reading agent that:

1. **Reads** RSS feeds (Lilian Weng, HuggingFace, ArXiv, OpenAI, The Gradient) and seed Wikipedia pages
2. **Fetches safely** — checks `robots.txt`, rate-limits, blocks private IPs, caps response size at 30 KB
3. **Extracts** readable text, stripping nav bars, ads, footers, and boilerplate
4. **Summarizes** using frequency-based extractive NLP (no external LLM APIs required)
5. **Generates** a reflective "My take" using a tiny local character-level GPT (or a template fallback)
6. **Commits** a Jekyll post and triggers GitHub Pages deployment

```
RSS feeds + seed URLs
        │
        ▼
  SafeFetcher
  (robots.txt ✓ · rate-limit ✓ · private-IP block ✓ · 30 KB cap ✓)
        │
        ▼
  HTML → readable text
  (BeautifulSoup · boilerplate stripped · PII redacted)
        │
        ▼
  Extractive summarizer
  (frequency-based · top-7 sentences · deduplication)
        │
        ▼
  Jekyll post writer
  (TL;DR · source links · key bullets)
        │
        ▼
  Tiny char-GPT "My take"
  (Shakespeare-trained · local · template fallback if missing)
        │
        ▼
  git commit → GitHub Pages deploy
```

---

## Repo layout

```
.
├── ghost_blogger_agent/        # The Python agent
│   ├── src/ghost_blogger/      # Core source
│   │   ├── agent.py            # Orchestration pipeline
│   │   ├── net.py              # SafeFetcher (robots.txt, rate-limit, policy)
│   │   ├── extract.py          # HTML → readable text (BeautifulSoup)
│   │   ├── summarize.py        # Frequency-based extractive summarizer
│   │   ├── write_post.py       # Jekyll markdown generator
│   │   ├── state.py            # Persistent state (seen URLs, last run)
│   │   ├── dedupe.py           # URL / title / fingerprint deduplication
│   │   └── llm/                # Voice generation
│   │       ├── tiny_char_gpt.py  # Tiny local character-level GPT
│   │       └── template.py       # Template fallback writer
│   ├── models/                 # Pre-trained checkpoint (char-GPT, Shakespeare)
│   ├── data/state.json         # Persistent run state
│   ├── config.yaml             # Sources, policy, output settings
│   ├── tests/                  # pytest suite
│   └── POLICY.md               # Formal safety policy
│
├── knowjoby-blog/              # Jekyll blog (GitHub Pages)
│   ├── _posts/                 # Auto-generated posts land here
│   ├── how-it-works.md         # Pipeline explainer (live on the blog)
│   ├── status.md               # Run history & post stats
│   └── _config.yml
│
└── .github/workflows/
    ├── ghost_blogger.yml       # Scheduled agent run (every 15 min, UTC)
    └── pages.yml               # Jekyll → GitHub Pages deploy
```

---

## Quick start (local)

```bash
cd ghost_blogger_agent
python3 -m venv .venv && source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
pip install -e . --no-deps

# Preview output without writing files
python -m ghost_blogger run --config config.yaml --dry-run

# Full run — writes a post to ../knowjoby-blog/_posts/
python -m ghost_blogger run --config config.yaml
```

**Optional:** enable the tiny local voice model (requires PyTorch):

```bash
pip install -e .[llm]
```

---

## Configuration

All knobs live in [`ghost_blogger_agent/config.yaml`](ghost_blogger_agent/config.yaml).

| Setting | Default | Description |
|---|---|---|
| `agent.max_pages_per_run` | `5` | Max URLs fetched per run |
| `agent.delay_s` | `2.0` | Polite delay between requests (seconds) |
| `policy.obey_robots_txt` | `true` | Respect robots.txt — fails closed if unreachable |
| `sources.feeds` | 5 feeds | RSS/Atom sources to poll |
| `sources.seed_urls` | 3 URLs | Fallback seed pages (Wikipedia AI articles) |
| `output.timezone` | `Asia/Kolkata` | Timestamp timezone for post front matter |
| `state.max_seen_age_days` | `60` | URL memory window (forget older entries) |

**Override without editing YAML:**

```bash
GHOST_MAX_PAGES_PER_RUN=10 \
GHOST_FEEDS="https://example.com/feed.xml,https://other.com/rss" \
python -m ghost_blogger run --config config.yaml
```

All environment overrides: `GHOST_POSTS_DIR`, `GHOST_MAX_PAGES_PER_RUN`, `GHOST_DELAY_S`, `GHOST_OBEY_ROBOTS_TXT`, `GHOST_FEEDS`, `GHOST_SEED_URLS`.

---

## Safety design

The agent is a **polite, passive reader** — it never creates accounts, never submits forms, and never bypasses paywalls.

- **HTTPS only** by default
- `robots.txt` obeyed; fails closed if the file cannot be fetched
- Private IPs, localhost, and metadata services are blocked at DNS resolution
- Max 5 redirects; non-standard ports rejected
- Response size capped at 30 KB per page
- PII patterns redacted from extracted text (`[redacted-email]`, `[redacted-phone]`)
- Deduplication across URL, title, and content fingerprint

Full policy: [`ghost_blogger_agent/POLICY.md`](ghost_blogger_agent/POLICY.md)

---

## GitHub Actions

| Workflow | Trigger | What it does |
|---|---|---|
| `ghost_blogger.yml` | cron `*/15 * * * *` (UTC, best-effort) | Runs agent, commits post if new content found |
| `pages.yml` | After `ghost_blogger.yml` completes | Builds Jekyll site, deploys to GitHub Pages |

No personal tokens required — the workflows use the built-in `GITHUB_TOKEN` with `contents: write` permission.

---

## Running tests

```bash
cd ghost_blogger_agent
pip install -r requirements-dev.txt
pytest -q
```

Tests cover: URL validation, HTML extraction, post generation, deduplication, and post structure validation.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

See [LICENSE](LICENSE).
