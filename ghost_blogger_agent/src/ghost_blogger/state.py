from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union


@dataclass
class State:
    seen_urls: set[str] = field(default_factory=set)
    last_run_utc: Optional[str] = None

    @classmethod
    def load(cls, path: Union[str, Path]) -> "State":
        p = Path(path)
        if not p.exists():
            return cls()
        raw = json.loads(p.read_text(encoding="utf-8"))
        return cls(
            seen_urls=set(raw.get("seen_urls", [])),
            last_run_utc=raw.get("last_run_utc"),
        )

    def save(self, path: Union[str, Path]) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(
                {"seen_urls": sorted(self.seen_urls), "last_run_utc": self.last_run_utc},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
