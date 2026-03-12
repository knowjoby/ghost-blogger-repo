from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ghost_blogger.config import LLMConfig

from .base import LLM, LLMInfo
from .template import TemplateLLM
from .tiny_char_gpt import TinyCharGPTLLM


def get_llm(cfg: LLMConfig) -> LLM:
    if cfg.kind == "tiny_char_gpt":
        ckpt = Path(cfg.checkpoint_path)
        vocab = Path(cfg.vocab_text_path)
        if not ckpt.exists() or not vocab.exists():
            return TemplateLLM(info=LLMInfo(kind="template", ok=True, detail="model files missing"))
        llm = TinyCharGPTLLM.try_create(
            checkpoint_path=ckpt,
            vocab_text_path=vocab,
            temperature=cfg.temperature,
            max_new_chars=cfg.max_new_chars,
        )
        if llm is not None:
            return llm
        return TemplateLLM(info=LLMInfo(kind="template", ok=True, detail="torch/model load failed"))

    return TemplateLLM(info=LLMInfo(kind="template", ok=True, detail="unknown llm.kind"))
