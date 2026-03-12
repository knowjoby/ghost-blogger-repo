# Requirements Handover (Product + Ops)

This document is the “what and why” counterpart to `HANDOVER.md` (which is the “how”).

Scope: `https://knowjoby.github.io/blog` — an automated AI news feed that publishes link-posts, plus an operator UI to verify freshness and diagnose issues quickly.

Last updated: **2026-03-12**.

---

## 1) Product goals

### Primary goal (CEO)

Ship a **high-signal, low-maintenance AI news briefing** that a busy operator (CEO/CTO) can scan daily in < 60 seconds.

### Secondary goals

- Keep the site **fresh automatically** without manual curation.
- Make failures **obvious and diagnosable** from the UI (no SSH, no logs spelunking).
- Avoid duplicates and spam; prioritize recency and relevance.

### Non-goals

- Full-text scraping, paywall bypass, or copying article bodies.
- Human editorial workflow / approvals.
- Real-time “breaking news” alerts (can be added later).

---

## 2) Personas & daily workflow

### Persona A: Reader (default)

Needs:
- “What happened?” (Top items)
- “What should I read?” (Links with source + score)
- “What’s new since I last looked?” (Highlight)

Daily flow:
1. Open homepage.
2. Scan top briefing.
3. Open 1–3 links.

### Persona B: Operator (CTO mode)

Needs:
- “Is it running?” (last run, last post age)
- “If it’s stale, why?” (DDG vs RSS, candidates found, posts created)
- “What’s queued?” (pending items not posted yet)

Daily flow:
1. If homepage seems stale → open Status.
2. Confirm runs are happening; check if candidates are 0 or if fetch failed.
3. Inspect Queue + Archives to validate relevance and dedupe.

---

## 3) Core features (must-have)

### F1 — Daily briefing on homepage

Requirements:
- Homepage contains:
  - a short **Briefing** block (top items from recent window)
  - the main feed (grouped by date)
- Feed supports:
  - tag filter
  - “new since last visit” highlight
  - “show older” pagination / expansion

Acceptance:
- Opening `/blog/` shows top items and at least the most recent N items without extra clicks.

### F2 — Automation reliability (DDG → RSS fallback)

Requirements:
- Generator tries DDG News first.
- If DDG yields no results or errors, fallback to RSS.
- No run should break the build due to malformed data.

Acceptance:
- A run on GitHub Actions produces either new posts, or a log stating “no candidates”, but does not crash.

### F3 — No duplication across published vs queued

Requirements:
- Dedup key is normalized URL.
- Published items must not appear in the Queue view.

Acceptance:
- Queue UI lists only URLs not present in published history.

### F4 — Operator status page

Requirements:
- Status page shows:
  - latest run metadata (time, trigger, candidates, posts created, queued)
  - feed stats (DDG/RSS counts when available)
  - recent run history table

Acceptance:
- Operator can answer “is it working?” and “what changed?” from one page.

### F5 — Queue visibility (public snapshot)

Requirements:
- Publish a sanitized queue snapshot to `_data/news_queue_public.json`:
  - contains only pending items
  - limited size (cap)
  - safe Unicode encoding for Jekyll data parsing

Acceptance:
- Jekyll build succeeds and Queue appears in the UI even on GitHub Pages.

---

## 4) Nice-to-have features (should-have)

### N1 — Stale-feed guardrail

Requirements:
- If last post is older than threshold (e.g., 18 hours), show an obvious banner on homepage.

Acceptance:
- Stale banner appears when threshold is exceeded, and links to Status/Archives.

### N2 — Sources transparency

Requirements:
- Document or render the RSS fallback sources list.

Acceptance:
- A user can see the source list without reading code.

---

## 5) Data & content requirements

### Posts

- Must be valid Jekyll posts under `_posts/`.
- Must include:
  - `categories: ai-news`
  - `score` (0–100)
  - `link` (outbound) OR internal post URL (fallback)
  - `source` when available

### Scoring

- Must bias toward:
  - recency
  - major AI labs/companies
  - meaningful topics (release, policy, safety, etc.)
- Must exclude irrelevant items even if “AI” appears.

### Queue state

- `data/news_queue.json` is the private state.
- `_data/news_queue_public.json` is the public/UI snapshot.

---

## 6) Non-functional requirements

### Performance

- Homepage must render quickly and remain usable with hundreds+ posts.
- Client-side operations (filters) must not freeze typical browsers.

### Reliability

- GitHub Pages build must not fail due to:
  - invalid JSON encoding
  - unexpected characters in titles/snippets
  - missing optional fields

### Security / safety

- Never store API keys in repo.
- Only outbound link posting; no copying third-party article text.
- Sanitize any UI-rendered data (escape in templates).

---

## 7) Operational requirements (GitHub Actions)

- Workflows must commit:
  - `_posts/`
  - `data/news_queue.json`
  - `_data/run_log.json`
  - `_data/news_queue_public.json`
- Deploy workflow must build and publish site on push to `main`.

---

## 8) Definition of Done (DoD) for changes

Every change that touches generator or templates must:

- `python3 -m py_compile scripts/generate_news.py`
- `bundle exec jekyll build`
- Not increase duplication across Published/Queue
- Preserve backward compatibility for `/now/` (redirect ok)

---

## 9) Future roadmap (ranked)

1. **Queue policy:** if no fresh candidates, publish from queue to maintain cadence (with guardrails).
2. **Health endpoint:** `/health/` single-line status: last post age + last run age.
3. **Source analytics:** basic per-source success rate and yield in Status.
4. **Better scoring transparency:** show score components for top items (optional).

