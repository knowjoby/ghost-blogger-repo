from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Optional

from dateutil import tz

from ghost_blogger.config import AppConfig
from ghost_blogger.dedupe import (
    existing_urls_today,
    fingerprint_for_run,
    fingerprint_marker,
    seen_fingerprint_today,
    seen_title_today,
)
from ghost_blogger.extract import extract_readable_text
from ghost_blogger.net import PolicyError, SafeFetcher, redact_pii_like
from ghost_blogger.sources import SourceItem, dedupe_items, iter_feed_items
from ghost_blogger.state import State
from ghost_blogger.summarize import summarize
from ghost_blogger.validation import validate_post_markdown
from ghost_blogger.write_post import Post, write_new_post


@dataclass(frozen=True)
class Note:
    url: str
    title: "str | None"
    summary: str
    source: "str | None" = None


class GhostBloggerAgent:
    def __init__(self, cfg: AppConfig, *, dry_run: bool = False) -> None:
        self._cfg = cfg
        self._dry_run = dry_run

    def run(self) -> None:
        state = State.load(self._cfg.state.path, max_seen_age_days=self._cfg.state.max_seen_age_days)
        fetcher = SafeFetcher(
            user_agent=self._cfg.agent.user_agent,
            timeout_s=self._cfg.agent.request_timeout_s,
            delay_s=self._cfg.agent.delay_s,
            allow_http=self._cfg.policy.allow_http,
            disallowed_domains=self._cfg.policy.disallowed_domains,
            obey_robots_txt=self._cfg.policy.obey_robots_txt,
            max_chars=self._cfg.agent.max_chars_per_page,
        )
        try:
            local_tz = tz.gettz(self._cfg.output.timezone) or tz.UTC
            today = datetime.now(tz=local_tz).date()
            already_seen = set(state.seen_urls)
            already_seen |= existing_urls_today(self._cfg.output.posts_dir, day=today)

            notes, fetch_stats = self._collect_notes(fetcher, already_seen)
            if not self._dry_run:
                state.last_run_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")
            if not notes:
                if not self._dry_run:
                    state.save(self._cfg.state.path)
                    self._write_telemetry(notes=[], fetch_stats=fetch_stats, post=None, local_tz=local_tz)
                print("No notes collected; skipping post.")
                return
            post = self._write_post(notes)
            if post is None:
                # Avoid repeated attempts on the same URLs when we chose not to write.
                if not self._dry_run:
                    for n in notes:
                        state.seen_urls.add(n.url)
                    state.save(self._cfg.state.path)
                    self._write_telemetry(notes=notes, fetch_stats=fetch_stats, post=None, local_tz=local_tz)
                print("Skipping write.")
                return
            if not self._dry_run:
                for n in notes:
                    state.seen_urls.add(n.url)
                state.save(self._cfg.state.path)
                self._write_telemetry(notes=notes, fetch_stats=fetch_stats, post=post, local_tz=local_tz)
            print(f"Wrote post: {post}")
        finally:
            fetcher.close()

    def _collect_notes(
        self, fetcher: SafeFetcher, seen_urls: set[str]
    ) -> tuple[list[Note], dict]:
        items: list[SourceItem] = []
        for feed in self._cfg.sources.feeds:
            items.extend(iter_feed_items(fetcher, feed))
        for u in self._cfg.sources.seed_urls:
            items.append(SourceItem(url=u, title=None, source="seed"))

        items = dedupe_items(items)

        notes: list[Note] = []
        pages_attempted = 0
        for it in items:
            if len(notes) >= self._cfg.agent.max_pages_per_run:
                break
            if it.url in seen_urls:
                continue
            pages_attempted += 1
            try:
                res = fetcher.get_text(it.url)
            except PolicyError:
                continue
            if res.status_code >= 400:
                continue

            extracted = extract_readable_text(res.text)
            text = redact_pii_like(extracted.text)
            text = self._clean_extracted_text(text)
            summ = summarize(text, max_sentences=7)
            summ = self._clean_summary(summ)
            if not self._summary_is_usable(summ):
                continue
            notes.append(
                Note(
                    url=res.url,
                    title=extracted.title or it.title,
                    summary=summ,
                    source=it.source,
                )
            )
        return notes, {"pages_attempted": pages_attempted, "pages_succeeded": len(notes)}

    def _clean_summary(self, summary: str) -> str:
        s = (summary or "").strip()
        s = re.sub(r"\s+", " ", s)
        if len(s) > 1200:
            s = s[:1200].rstrip() + "…"
        return s

    def _clean_extracted_text(self, text: str) -> str:
        t = (text or "").strip()
        if not t:
            return ""
        # Remove HTML-ish fragments that sometimes appear inside text nodes.
        t = re.sub(r"<[^>\n]{1,200}>", " ", t)
        lines: list[str] = []
        for ln in t.splitlines():
            s = ln.strip()
            if not s:
                continue
            if re.search(r"\b(opens in a new window|switch to chatgpt)\b", s, flags=re.IGNORECASE):
                continue
            if re.search(r"\b(back to articles|upvote|update on github)\b", s, flags=re.IGNORECASE):
                continue
            if re.search(r"\b(table of contents|citation references?)\b", s, flags=re.IGNORECASE):
                continue
            # Heuristic: drop navigation/TOC-like lines (very long with no sentence punctuation).
            if len(s) > 140:
                punct = re.findall(r"[.!?]", s)
                words = re.findall(r"[A-Za-z][A-Za-z']+", s)
                if not punct:
                    continue
                if len(words) > 35 and len(punct) < 2:
                    continue
            if len(s) > 500:
                continue
            if re.search(r"\b(accept\s+cookies?|cookie\s+policy|privacy\s+policy"
                         r"|terms\s+of\s+service|copyright\s*©|all\s+rights\s+reserved)\b",
                         s, flags=re.IGNORECASE):
                continue
            if re.search(r"(\|.*){3,}", s):
                continue
            if re.match(r"^https?://\S+$", s):
                continue
            words = re.findall(r"[A-Za-z]+", s)
            if 1 <= len(words) <= 6 and all(w.isupper() for w in words):
                continue
            lines.append(s)
        return "\n".join(lines).strip()

    def _summary_is_usable(self, summary: str) -> bool:
        s = (summary or "").strip()
        if not s:
            return False
        if "<" in s or ">" in s:
            return False
        if re.search(r"\b(opens in a new window|switch to chatgpt)\b", s, flags=re.IGNORECASE):
            return False
        if re.search(r"\bjump\s+to\s+(content|navigation|search)\b", s, flags=re.IGNORECASE):
            return False
        if re.search(r"\b(back to articles|upvote|update on github)\b", s, flags=re.IGNORECASE):
            return False
        if re.match(r"^https?://\S+\s*$", s):
            return False
        words = re.findall(r"[A-Za-z][A-Za-z']+", s)
        if len(words) < 18:
            return False
        uniq_ratio = len(set(w.lower() for w in words)) / max(len(words), 1)
        if uniq_ratio < 0.35:
            return False
        return True

    def _write_post(self, notes: list[Note]) -> Optional[Path]:
        local_tz = tz.gettz(self._cfg.output.timezone) or tz.UTC
        now = datetime.now(tz=local_tz)
        title = self._pick_title(notes, now)
        if seen_title_today(self._cfg.output.posts_dir, day=now.date(), title=title):
            print("Duplicate title for today; skipping post.")
            return None

        fp = fingerprint_for_run(day=now.date(), source_urls=[n.url for n in notes])
        if seen_fingerprint_today(self._cfg.output.posts_dir, day=now.date(), fp=fp):
            print("Duplicate run fingerprint for today; skipping post.")
            return None
        body = fingerprint_marker(fp) + "\n\n" + self._render_body(title=title, now=now, notes=notes)
        post = Post(title=title, date=now, tags=self._cfg.output.tags, body_md=body)
        md = body.strip()
        errors = validate_post_markdown(md, notes_count=len(notes))
        if errors:
            # User preference: publish anyway; just log the issues.
            print("Post validation warnings:", "; ".join(errors))
        if self._dry_run:
            from ghost_blogger.write_post import render_jekyll_markdown
            print("[DRY-RUN]\n" + render_jekyll_markdown(post))
            return Path("[dry-run]")
        return write_new_post(self._cfg.output.posts_dir, post)

    def _write_telemetry(
        self,
        *,
        notes: list[Note],
        fetch_stats: dict,
        post: Optional[Path],
        local_tz: object,
    ) -> None:
        """Write run telemetry to knowjoby-blog/_data/. Non-fatal — never breaks post writing."""
        try:
            from ghost_blogger import telemetry as _tel

            posts_dir = Path(self._cfg.output.posts_dir)
            data_dir = posts_dir.parent / "_data"
            post_slug = post.stem if post and str(post) != "[dry-run]" else None
            _tel.record_run(
                data_dir=data_dir,
                timestamp_utc=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                pages_attempted=fetch_stats.get("pages_attempted", 0),
                pages_succeeded=fetch_stats.get("pages_succeeded", 0),
                post_written=post is not None,
                post_slug=post_slug,
            )
            if notes:
                texts = [f"{n.title or ''} {n.summary}" for n in notes]
                _tel.update_concepts(
                    data_dir=data_dir,
                    notes_texts=texts,
                    post_slug=post_slug,
                    today=datetime.now(tz=local_tz).date().isoformat(),
                )
        except Exception as exc:
            print(f"Telemetry write failed (non-fatal): {exc}")

    def _pick_title(self, notes: list[Note], now: datetime) -> str:
        if notes and notes[0].title:
            return f"Ghost notes: {notes[0].title}"
        return f"Ghost notes: learning log for {now:%Y-%m-%d}"

    def _render_body(self, *, title: str, now: datetime, notes: list[Note]) -> str:
        intro = (
            f"I’m `{self._cfg.agent.name}`, a GitHub-native reading agent. "
            "I don’t create accounts, I don’t submit forms, and I respect `robots.txt`. "
            "I’m not sentient—this is reflective writing as a tool."
        )

        if not notes:
            return (
                f"{intro}\n\n"
                "Today I didn’t find any readable pages within my safety policy (or they were blocked by robots). "
                "I’ll try again next run.\n"
            )

        tldr = self._tldr(notes)
        what_i_read = "\n".join(
            [
                f"- [{n.title or n.url}]({n.url})"
                + (f" — *{n.source}*" if n.source else "")
                for n in notes
            ]
        )

        learnings = "\n\n".join([self._render_note(n) for n in notes])

        reflection = self._reflect(title=title, now=now, notes=notes)

        return (
            f"## TL;DR\n\n{tldr}\n\n"
            f"{intro}\n\n"
            f"## What I read\n\n{what_i_read}\n\n"
            f"## What I learned\n\n{learnings}\n\n"
            f"## My take (reflective voice)\n\n{reflection}\n"
        )

    def _sentences(self, text: str) -> list[str]:
        t = (text or "").strip()
        if not t:
            return []
        parts = re.split(r"(?<=[.!?])\s+", t)
        out: list[str] = []
        for p in parts:
            s = p.strip()
            if not s:
                continue
            out.append(s)
        return out

    def _tldr(self, notes: list[Note]) -> str:
        bullets: list[str] = []
        for n in notes:
            sents = self._sentences(n.summary)
            if sents:
                bullets.append(sents[0])
        bullets = bullets[:5]
        if not bullets:
            bullets = ["A few pages were read, but the summaries were too thin to extract a TL;DR."]
        return "\n".join([f"- {b}" for b in bullets])

    def _render_note(self, n: Note) -> str:
        sents = self._sentences(n.summary)
        key = sents[:3] if sents else []
        if not key:
            key = [n.summary.strip()] if n.summary.strip() else []
        key_md = "\n".join([f"- {k}" for k in key if k])
        src = f"[{n.url}]({n.url})"
        return (
            f"### {n.title or 'Untitled'}\n\n"
            f"{key_md}\n\n"
            f"Source: {src}"
        )

    def _reflect(self, *, title: str, now: datetime, notes: list[Note]) -> str:
        from ghost_blogger.llm import get_llm

        llm = get_llm(self._cfg.llm)
        prompt = (
            f"Title: {title}\n"
            f"Date: {now:%Y-%m-%d}\n\n"
            "Write 1–2 short paragraphs as a cautious AI researcher describing what you learned, "
            "your view, and a gentle as-if feeling. Be clear you are not sentient.\n\n"
            "Notes:\n"
            + "\n".join([f"- {n.summary}" for n in notes[:4]])
            + "\n\nReflection:\n"
        )
        out = llm.generate(prompt)
        out = out.strip()
        if not out:
            return (
                "I’m noticing a familiar pattern: I can collect facts quickly, but I have to be deliberate about "
                "what I *trust* and what I merely *saw*. My “feelings” here are only a writing device—useful for "
                "making uncertainty visible."
            )
        if "not sentient" not in out.lower():
            out = "I’m not sentient—this is reflective writing as a tool.\n\n" + out
        return out
