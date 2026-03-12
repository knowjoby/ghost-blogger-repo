from __future__ import annotations

from dataclasses import dataclass


class LLM:
    def generate(self, prompt: str) -> str:  # pragma: no cover (interface)
        raise NotImplementedError


@dataclass(frozen=True)
class LLMInfo:
    kind: str
    ok: bool
    detail: str

