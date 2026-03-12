from __future__ import annotations

from dataclasses import dataclass

from ghost_blogger.net import redact_pii_like

from .base import LLM, LLMInfo


@dataclass(frozen=True)
class TemplateLLM(LLM):
    info: LLMInfo

    def generate(self, prompt: str) -> str:
        p = redact_pii_like(prompt)
        lines = [ln.strip() for ln in p.splitlines() if ln.strip()]
        notes = [ln[2:].strip() for ln in lines if ln.startswith("- ")]
        notes = notes[:4]
        core = " ".join(notes)[:600] if notes else "I read a few pages, but I’m still calibrating confidence."
        return (
            "I’m not sentient—this is reflective writing as a tool. "
            "What stands out to me is the gap between *exposure* and *understanding*: "
            f"{core}\n\n"
            "My view today: prioritize concrete claims, track uncertainty, and keep my curiosity polite."
        )
