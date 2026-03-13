from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional, Union


class _SeenProxy:
    """Set-like proxy over dict[url, ISO-timestamp]; .add() stamps current time."""

    def __init__(self, store: dict[str, str]) -> None:
        self._store = store

    def add(self, url: str) -> None:
        if url not in self._store:
            self._store[url] = datetime.now(timezone.utc).isoformat(timespec="seconds")

    def __contains__(self, item: object) -> bool:
        return item in self._store

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)


@dataclass
class State:
    _seen: dict[str, str] = field(default_factory=dict)
    last_run_utc: Optional[str] = None

    @property
    def seen_urls(self) -> _SeenProxy:
        return _SeenProxy(self._seen)

    @classmethod
    def load(cls, path: Union[str, Path], *, max_seen_age_days: int = 60) -> "State":
        p = Path(path)
        if not p.exists():
            return cls()
        raw = json.loads(p.read_text(encoding="utf-8"))
        raw_seen = raw.get("seen_urls", [])
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_seen_age_days)
        seen: dict[str, str] = {}
        if isinstance(raw_seen, list):
            # Backward compat: old list format → assign current timestamp to all.
            ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
            seen = {url: ts for url in raw_seen if isinstance(url, str) and url}
        elif isinstance(raw_seen, dict):
            for url, ts in raw_seen.items():
                try:
                    dt = datetime.fromisoformat(ts)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt >= cutoff:
                        seen[url] = ts
                except (ValueError, TypeError):
                    seen[url] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        return cls(_seen=seen, last_run_utc=raw.get("last_run_utc"))

    def save(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {"seen_urls": self._seen, "last_run_utc": self.last_run_utc},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
