---
layout: page
title: About
---

Signal Log is an automated AI news feed — a personal linklog tracking what’s happening across the AI industry.

**What it covers**

Releases, product launches, controversies, safety incidents, funding rounds, and anything notable from companies like Anthropic, OpenAI, Google DeepMind, Microsoft, Meta, xAI, and others building AI models.

**How to use it (daily)**

- Start on the homepage for the latest posts, grouped by day
- Use search + quick filters (OpenAI / Anthropic / Google / Microsoft / NVIDIA) to skim what matters fast
- Open **Read more** for extra links not yet published (a backlog, deduped against posted items)
- Use [Archives]({{ "/archives/" | relative_url }}) to browse everything with search, tags, and pagination
- Check [Changelog]({{ "/changelog/" | relative_url }}) for what changed

**How it works**

An automation runs continuously (every ~30 minutes) and:

1. Fetches fresh AI news (DDG News when available; RSS fallback when DDG is blocked on runners)
2. Filters for AI relevance (company + topic keyword rules)
3. Ranks stories internally (recency + importance)
4. Publishes selected items as posts (usually outbound links)
5. Commits to `main`, which triggers an automatic GitHub Pages deploy

No paywalls bypassed, no scraping tricks — just public headlines + links.

**Sources**

RSS fallback sources:

{% assign sources = site.data.rss_sources | default: "" %}
{% if sources and sources.size > 0 %}
<ul>
{% for s in sources %}
  <li><a href="{{ s.url }}" target="_blank" rel="noopener">{{ s.name }}</a></li>
{% endfor %}
</ul>
{% else %}
(No RSS sources file found.)
{% endif %}

**Tags**

Each post is auto-tagged by company (`anthropic`, `openai`, `google` …) and topic (`release`, `controversy`, `safety`, `rumor` …) so you can skim by what matters to you.

**Logs**

The [Status]({{ "/logs/" | relative_url }}) page shows the latest run + recent run history (plus quick diagnostics when something looks stale).
