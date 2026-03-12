---
layout: page
title: Archives
permalink: /archives/
---

All posts:

<ul>
  {%- for post in site.posts -%}
    <li>
      <span style="color:#888; font-size: 12px;">{{ post.date | date: "%Y-%m-%d" }}</span>
      <a href="{{ post.url | relative_url }}">{{ post.title | escape }}</a>
      {%- if post.tags and post.tags.size > 0 -%}
        <span style="color:#888; font-size: 12px;">· {{ post.tags | join: ", " }}</span>
      {%- endif -%}
    </li>
  {%- endfor -%}
</ul>

