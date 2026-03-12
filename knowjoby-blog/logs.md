---
layout: page
title: Status
permalink: /logs/
---

This page is the operational dashboard for Signal Log.

## Automation

- **Smart fetch (every 30 minutes):** finds + posts new AI news (commits to `main`)
- **Deploy:** GitHub Pages rebuilds automatically on every push to `main`

Quick links: [Home]({{ "/" | relative_url }}) · [Archives]({{ "/archives/" | relative_url }}) · [Changelog]({{ "/changelog/" | relative_url }})

## Latest run

{% assign runs = site.data.run_log | default: "" %}
{% if runs and runs.size > 0 %}
  {% assign last = runs | last %}

**Ran at:** {{ last.ran_at | default: "unknown" }}  
**Triggered by:** {{ last.triggered_by | default: "unknown" }}  
**Candidates found:** {{ last.candidates_found | default: 0 }}  
**Posts created:** {{ last.posts_created | default: 0 }}  
**Read more added:** {{ last.queued | default: 0 }}

{% if last.feeds %}
### Feeds

{% if last.feeds.ddg %}
- **DDG:** {{ last.feeds.ddg.raw | default: "?" }} raw → {{ last.feeds.ddg.candidates | default: "?" }} candidates
{% endif %}
{% if last.feeds.rss %}
- **RSS:** {{ last.feeds.rss.raw | default: "?" }} raw → {{ last.feeds.rss.candidates | default: "?" }} candidates (ok: {{ last.feeds.rss.feeds_ok | default: "?" }}, failed: {{ last.feeds.rss.feeds_failed | default: "?" }})
{% endif %}
{% endif %}

{% if last.posts and last.posts.size > 0 %}
### Posts created

{% for p in last.posts %}
- {% if p.file %}[{{ p.title }}]({{ p.file | relative_url }}){% else %}{{ p.title }}{% endif %}
{% endfor %}
{% else %}
### Posts created

No posts created on the latest run.
{% endif %}

## Recent run history

<table>
  <thead>
    <tr>
      <th>Ran at</th>
      <th>Trigger</th>
      <th>Candidates</th>
      <th>Posts</th>
      <th>Read more</th>
    </tr>
  </thead>
  <tbody>
  {% assign recent = runs | reverse %}
  {% for r in recent limit: 20 %}
    <tr>
      <td>{{ r.ran_at | default: "unknown" }}</td>
      <td>{{ r.triggered_by | default: "unknown" }}</td>
      <td>{{ r.candidates_found | default: 0 }}</td>
      <td>{{ r.posts_created | default: 0 }}</td>
      <td>{{ r.queued | default: 0 }}</td>
    </tr>
  {% endfor %}
  </tbody>
</table>

{% else %}
No run logs found. The automation hasn’t written `_data/run_log.json` yet.
{% endif %}
