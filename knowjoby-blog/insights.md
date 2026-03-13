---
layout: page
title: Insights
permalink: /insights/
---

Live telemetry from the autonomous maintenance cycle — feed health, concept trends, and the improvement log.

---

## Feed Health

{% if site.data.analysis.feed_health %}
<table>
<thead><tr><th>Feed</th><th>Status</th></tr></thead>
<tbody>
{% for feed in site.data.analysis.feed_health %}
<tr>
  <td><code>{{ feed[0] }}</code></td>
  <td>
    {% if feed[1].reachable %}
      <span class="dot dot-green dot-pulse"></span><span class="score-badge score-high">{{ feed[1].status_code }}</span>
    {% else %}
      <span class="dot dot-orange"></span><span class="score-badge score-low">unreachable</span>
    {% endif %}
  </td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
_Feed health data not yet available. The analyst runs daily at 06:00 UTC._
{% endif %}

---

## Stats

{% if site.data.analysis.run_success_rate_7d %}
{% assign pct = site.data.analysis.run_success_rate_7d | times: 100 | round %}
<div class="stat-grid" style="margin:12px 0 20px">
  <div class="stat-card">
    <span class="num">{{ pct }}%</span>
    <span class="label">runs → post (7d)</span>
  </div>
  {% if site.data.analysis.top_concepts_7d %}
  <div class="stat-card">
    <span class="num">{{ site.data.analysis.top_concepts_7d | size }}</span>
    <span class="label">active concepts</span>
  </div>
  {% endif %}
  {% if site.data.analysis.concept_gaps %}
  <div class="stat-card">
    <span class="num">{{ site.data.analysis.concept_gaps | size }}</span>
    <span class="label">concept gaps</span>
  </div>
  {% endif %}
</div>
{% else %}
_Not yet computed._
{% endif %}

---

## Top Concepts (7 days)

{% if site.data.analysis.top_concepts_7d and site.data.analysis.top_concepts_7d.size > 0 %}
{% for concept in site.data.analysis.top_concepts_7d %}
<span class="score-badge score-high" style="margin:2px">{{ concept }}</span>
{% endfor %}
{% else %}
_No concept data yet._
{% endif %}

---

## Improvement Log

{% if site.data.improvement_log and site.data.improvement_log.size > 0 %}
<table>
<thead><tr><th>Timestamp</th><th>Result</th><th>Changes</th></tr></thead>
<tbody>
{% assign recent_log = site.data.improvement_log | reverse %}
{% for entry in recent_log limit:10 %}
<tr>
  <td style="white-space:nowrap;color:var(--text-muted)">{{ entry.timestamp | replace: "T", " " | slice: 0, 16 }}</td>
  <td>{% if entry.success %}<span class="score-badge score-high">ok</span>{% else %}<span class="score-badge score-low">failed</span>{% endif %}</td>
  <td style="font-size:0.82em">{{ entry.changes | join: " &middot; " }}{% if entry.failure_reason %}<span style="color:var(--err)"> {{ entry.failure_reason | truncate: 80 }}</span>{% endif %}</td>
</tr>
{% endfor %}
</tbody>
</table>
{% else %}
_No improvements logged yet._
{% endif %}

---

<span style="font-family:'JetBrains Mono',monospace;font-size:0.7em;color:var(--text-muted)">last analysis: {{ site.data.analysis.generated | default: "never" }}</span>
