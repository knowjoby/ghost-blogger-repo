---
layout: page
title: Archives
permalink: /archives/
---

Two views:

- **Published:** what’s already on the blog
- **Read more:** extra links not yet published (deduped)

Tip: use search + tag chips to filter; pagination keeps it fast even with hundreds of links.

<div style="display:flex; gap:10px; align-items:center; margin: 16px 0; flex-wrap: wrap;">
  <input id="archiveSearch" type="text" placeholder="Search title, source, tags…" style="flex:1 1 280px; padding:10px 12px; border:1px solid #ddd; border-radius:8px;">
  <button id="archiveClear" type="button" style="padding:10px 12px; border:1px solid #ddd; border-radius:8px; background:#fff; cursor:pointer;">Clear</button>
</div>

<div style="display:flex; gap:10px; flex-wrap: wrap; margin: 10px 0 14px;">
  <button id="tabPublished" type="button" style="padding:8px 12px; border-radius:999px; border:1px solid #ddd; background:#f6f8fa; cursor:pointer;">Published</button>
  <button id="tabQueue" type="button" style="padding:8px 12px; border-radius:999px; border:1px solid #ddd; background:#fff; cursor:pointer;">Read more</button>
  <span id="queueMeta" style="align-self:center; color:#888; font-size:12px;"></span>
</div>

<div id="archiveActiveFilter" style="display:none; margin: 8px 0; padding: 8px 12px; border-radius: 8px; background: #f6f8fa; border: 1px solid #eee; font-size: 14px;"></div>

<table id="archiveTablePublished">
  <thead>
    <tr>
      <th style="text-align:left;">Date</th>
      <th style="text-align:left;">Title</th>
      <th style="text-align:left;">Source</th>
      <th style="text-align:left;">Tags</th>
    </tr>
  </thead>
  <tbody>
  {%- assign posts = site.posts | where_exp: "post", "post.categories contains 'ai-news'" -%}
  {%- for post in posts -%}
    {%- assign tags = post.tags | join: " " -%}
    {%- assign source = post.source | default: "" -%}
    {%- if post.link -%}
      {%- assign href = post.link -%}
      {%- assign target = "_blank" -%}
      {%- assign rel = "noopener" -%}
    {%- else -%}
      {%- assign href = post.url | relative_url -%}
      {%- assign target = "" -%}
      {%- assign rel = "" -%}
    {%- endif -%}

    <tr class="archiveRow archiveRowPublished"
        data-title="{{ post.title | escape | replace: '&amp;#8217;', '’' | replace: '&#8217;', '’' | replace: '&amp;rsquo;', '’' | replace: '&rsquo;', '’' | downcase }}"
        data-source="{{ source | downcase }}"
        data-tags="{{ tags | downcase }}">
      <td style="white-space:nowrap;">{{ post.date | date: "%Y-%m-%d" }}</td>
      <td>
        <a href="{{ href }}"{% if target != "" %} target="{{ target }}"{% endif %}{% if rel != "" %} rel="{{ rel }}"{% endif %}>
          {{ post.title | escape | replace: '&amp;#8217;', '’' | replace: '&#8217;', '’' | replace: '&amp;rsquo;', '’' | replace: '&rsquo;', '’' }}
        </a>
      </td>
      <td style="white-space:nowrap;">{{ source }}</td>
      <td>
        {%- if post.tags and post.tags.size > 0 -%}
          {%- for tag in post.tags -%}
            <button type="button" class="archiveTag" data-tag="{{ tag | downcase }}" style="margin:2px 4px 2px 0; padding:2px 8px; border-radius:999px; border:1px solid #eee; background:#f8f9fa; cursor:pointer; font-size:12px;">
              {{ tag }}
            </button>
          {%- endfor -%}
        {%- endif -%}
      </td>
    </tr>
  {%- endfor -%}
  </tbody>
</table>

{%- assign q = site.data.news_queue_public -%}
<table id="archiveTableQueue" style="display:none;">
  <thead>
    <tr>
      <th style="text-align:left;">Fetched</th>
      <th style="text-align:left;">Title</th>
      <th style="text-align:left;">Source</th>
      <th style="text-align:left;">Tags</th>
    </tr>
  </thead>
  <tbody>
  {%- if q and q.pending and q.pending.size > 0 -%}
    {%- for item in q.pending -%}
      {%- assign companies = item.companies | default: "" -%}
      {%- assign topics = item.topics | default: "" -%}
      {%- assign tag_str = "" -%}
      {%- if companies and companies.size > 0 -%}{%- assign tag_str = companies | join: " " -%}{%- endif -%}
      {%- if topics and topics.size > 0 -%}
        {%- assign topics_joined = topics | join: " " -%}
        {%- assign tag_str = tag_str | append: " " | append: topics_joined -%}
      {%- endif -%}
      <tr class="archiveRow archiveRowQueue"
          data-title="{{ item.title | escape | replace: '&amp;#8217;', '’' | replace: '&#8217;', '’' | replace: '&amp;rsquo;', '’' | replace: '&rsquo;', '’' | downcase }}"
          data-source="{{ item.source | default: '' | downcase }}"
          data-tags="{{ tag_str | downcase }}">
        <td style="white-space:nowrap;">{{ item.fetched_at | default: "" }}</td>
        <td>
          <a href="{{ item.url }}" target="_blank" rel="noopener">
            {{ item.title | escape | replace: '&amp;#8217;', '’' | replace: '&#8217;', '’' | replace: '&amp;rsquo;', '’' | replace: '&rsquo;', '’' }}
          </a>
        </td>
        <td style="white-space:nowrap;">{{ item.source | default: "" }}</td>
        <td>
          {%- if item.companies and item.companies.size > 0 -%}
            {%- for tag in item.companies -%}
              <button type="button" class="archiveTag" data-tag="{{ tag | downcase }}" style="margin:2px 4px 2px 0; padding:2px 8px; border-radius:999px; border:1px solid #eee; background:#f8f9fa; cursor:pointer; font-size:12px;">
                {{ tag }}
              </button>
            {%- endfor -%}
          {%- endif -%}
          {%- if item.topics and item.topics.size > 0 -%}
            {%- for tag in item.topics -%}
              <button type="button" class="archiveTag" data-tag="{{ tag | downcase }}" style="margin:2px 4px 2px 0; padding:2px 8px; border-radius:999px; border:1px solid #eee; background:#f8f9fa; cursor:pointer; font-size:12px;">
                {{ tag }}
              </button>
            {%- endfor -%}
          {%- endif -%}
        </td>
      </tr>
    {%- endfor -%}
  {%- else -%}
    <tr><td colspan="4" style="color:#888;">Read-more data not available yet (wait for the next automation run).</td></tr>
  {%- endif -%}
  </tbody>
</table>

<p id="archiveCount" style="margin-top: 12px; color: #666;"></p>

<div id="archivePager" style="display:flex; gap:10px; align-items:center; margin: 10px 0; flex-wrap: wrap;">
  <button id="pagePrev" type="button" style="padding:8px 12px; border-radius:8px; border:1px solid #ddd; background:#fff; cursor:pointer;">Prev</button>
  <button id="pageNext" type="button" style="padding:8px 12px; border-radius:8px; border:1px solid #ddd; background:#fff; cursor:pointer;">Next</button>
  <span id="pageInfo" style="color:#888; font-size:12px;"></span>
  <span style="margin-left:auto; color:#888; font-size:12px;">Rows/page</span>
  <select id="rowsPerPage" style="padding:8px 10px; border-radius:8px; border:1px solid #ddd; background:#fff;">
    <option value="25">25</option>
    <option value="50" selected>50</option>
    <option value="100">100</option>
    <option value="200">200</option>
  </select>
</div>

<script>
  (function() {
    var searchEl = document.getElementById('archiveSearch');
    var clearEl = document.getElementById('archiveClear');
    var activeEl = document.getElementById('archiveActiveFilter');
    var tabPublished = document.getElementById('tabPublished');
    var tabQueue = document.getElementById('tabQueue');
    var tablePublished = document.getElementById('archiveTablePublished');
    var tableQueue = document.getElementById('archiveTableQueue');
    var queueMeta = document.getElementById('queueMeta');

    var LS_PREFIX = 'signal_log_';
    var LS_ARCHIVE_TAB = LS_PREFIX + 'archive_tab';
    var LS_ARCHIVE_QUERY = LS_PREFIX + 'archive_query';
    var LS_ARCHIVE_TAG = LS_PREFIX + 'archive_tag';

    var activeTab = 'published';
    var activeTag = null;
    var currentPage = 1;
    var rowsPerPage = 50;

    var rowsPublished = Array.from(document.querySelectorAll('.archiveRowPublished'));
    var rowsQueue = Array.from(document.querySelectorAll('.archiveRowQueue'));

    {% if q and q.updated_at_utc %}
      {% assign updated_epoch = q.updated_at_utc | date: "%s" | plus: 0 %}
      {% assign updated_ist_epoch = updated_epoch | plus: 19800 %}
      queueMeta.textContent = 'Read more updated: {{ updated_ist_epoch | date: "%b %-d, %Y %H:%M" }} IST';
    {% endif %}

    var pagePrev = document.getElementById('pagePrev');
    var pageNext = document.getElementById('pageNext');
    var pageInfo = document.getElementById('pageInfo');
    var rowsPerPageEl = document.getElementById('rowsPerPage');

    function getRows() {
      return (activeTab === 'queue') ? rowsQueue : rowsPublished;
    }

    function applyPagination(visibleRows) {
      var total = visibleRows.length;
      var totalPages = Math.max(1, Math.ceil(total / rowsPerPage));
      if (currentPage > totalPages) currentPage = totalPages;
      if (currentPage < 1) currentPage = 1;

      var start = (currentPage - 1) * rowsPerPage;
      var end = start + rowsPerPage;

      visibleRows.forEach(function(row, idx) {
        row.style.display = (idx >= start && idx < end) ? '' : 'none';
      });

      pagePrev.disabled = currentPage <= 1;
      pageNext.disabled = currentPage >= totalPages;
      pagePrev.style.opacity = pagePrev.disabled ? '0.5' : '1';
      pageNext.style.opacity = pageNext.disabled ? '0.5' : '1';
      pageInfo.textContent = 'Page ' + currentPage + ' / ' + totalPages;
    }

    function applyFilter() {
      var q = (searchEl.value || '').trim().toLowerCase();
      var visible = 0;
      var rows = getRows();
      var visibleRows = [];

      rows.forEach(function(row) {
        var hay = [row.dataset.title, row.dataset.source, row.dataset.tags].join(' ');
        var ok = true;
        if (q && hay.indexOf(q) === -1) ok = false;
        if (activeTag && row.dataset.tags.indexOf(activeTag) === -1) ok = false;
        if (ok) {
          visible++;
          visibleRows.push(row);
        }
      });

      var msg = [];
      if (activeTag) msg.push('tag: ' + activeTag);
      if (q) msg.push('search: ' + q);
      if (msg.length > 0) {
        activeEl.textContent = 'Filtering by ' + msg.join(' • ');
        activeEl.style.display = 'block';
      } else {
        activeEl.style.display = 'none';
      }

      document.getElementById('archiveCount').textContent = visible + ' shown';

      try {
        localStorage.setItem(LS_ARCHIVE_QUERY, q || '');
        localStorage.setItem(LS_ARCHIVE_TAG, activeTag || '');
      } catch (e) {}

      // Pagination after filter
      currentPage = 1;
      applyPagination(visibleRows);
    }

    function wireTagButtons() {
      document.querySelectorAll('.archiveTag').forEach(function(btn) {
        btn.addEventListener('click', function() {
          var t = btn.dataset.tag;
          activeTag = (activeTag === t) ? null : t;
          applyFilter();
        });
      });
    }

    function setTab(tab, opts) {
      activeTab = tab;
      tabPublished.style.background = (tab === 'published') ? '#f6f8fa' : '#fff';
      tabQueue.style.background = (tab === 'queue') ? '#f6f8fa' : '#fff';
      tablePublished.style.display = (tab === 'published') ? '' : 'none';
      tableQueue.style.display = (tab === 'queue') ? '' : 'none';
      if (!(opts && opts.preserveTag)) activeTag = null;
      currentPage = 1;
      try { localStorage.setItem(LS_ARCHIVE_TAB, tab); } catch (e) {}
      applyFilter();
    }

    tabPublished.addEventListener('click', function() { setTab('published'); });
    tabQueue.addEventListener('click', function() { setTab('queue'); });

    searchEl.addEventListener('input', applyFilter);
    clearEl.addEventListener('click', function() {
      activeTag = null;
      searchEl.value = '';
      try {
        localStorage.removeItem(LS_ARCHIVE_QUERY);
        localStorage.removeItem(LS_ARCHIVE_TAG);
      } catch (e) {}
      applyFilter();
    });

    wireTagButtons();

    // Restore last view
    try {
      var savedTab = (localStorage.getItem(LS_ARCHIVE_TAB) || '').trim();
      var savedQuery = localStorage.getItem(LS_ARCHIVE_QUERY) || '';
      var savedTag = (localStorage.getItem(LS_ARCHIVE_TAG) || '').trim();
      if (savedQuery) searchEl.value = savedQuery;
      activeTag = savedTag ? savedTag : null;
      setTab(savedTab === 'queue' ? 'queue' : 'published', { preserveTag: true });
    } catch (e) {
      setTab('published');
    }

    // Keyboard shortcuts: "/" focus search, "Esc" clear
    document.addEventListener('keydown', function(e) {
      var t = e.target;
      var isTyping = t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable);
      if (!isTyping && e.key === '/') {
        e.preventDefault();
        if (searchEl) searchEl.focus();
      }
      if (e.key === 'Escape') {
        activeTag = null;
        searchEl.value = '';
        try {
          localStorage.removeItem(LS_ARCHIVE_QUERY);
          localStorage.removeItem(LS_ARCHIVE_TAG);
        } catch (e) {}
        applyFilter();
      }
    });

    pagePrev.addEventListener('click', function() {
      if (currentPage > 1) currentPage--;
      var rows = getRows();
      var q = (searchEl.value || '').trim().toLowerCase();
      var visibleRows = rows.filter(function(row) {
        var hay = [row.dataset.title, row.dataset.source, row.dataset.tags].join(' ');
        if (q && hay.indexOf(q) === -1) return false;
        if (activeTag && row.dataset.tags.indexOf(activeTag) === -1) return false;
        return true;
      });
      applyPagination(visibleRows);
    });

    pageNext.addEventListener('click', function() {
      currentPage++;
      var rows = getRows();
      var q = (searchEl.value || '').trim().toLowerCase();
      var visibleRows = rows.filter(function(row) {
        var hay = [row.dataset.title, row.dataset.source, row.dataset.tags].join(' ');
        if (q && hay.indexOf(q) === -1) return false;
        if (activeTag && row.dataset.tags.indexOf(activeTag) === -1) return false;
        return true;
      });
      applyPagination(visibleRows);
    });

    rowsPerPageEl.addEventListener('change', function() {
      rowsPerPage = parseInt(rowsPerPageEl.value, 10) || 50;
      currentPage = 1;
      applyFilter();
    });
  })();
</script>
