from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

import yaml


@dataclass(frozen=True)
class AgentConfig:
    name: str
    user_agent: str
    max_pages_per_run: int
    max_chars_per_page: int
    request_timeout_s: int
    delay_s: float


@dataclass(frozen=True)
class PolicyConfig:
    allow_http: bool
    obey_robots_txt: bool
    disallowed_domains: list[str]


@dataclass(frozen=True)
class SourcesConfig:
    feeds: list[str]
    seed_urls: list[str]


@dataclass(frozen=True)
class OutputConfig:
    posts_dir: str
    timezone: str
    tags: list[str]


@dataclass(frozen=True)
class StateConfig:
    path: str


@dataclass(frozen=True)
class LLMConfig:
    kind: str
    checkpoint_path: str
    vocab_text_path: str
    temperature: float
    max_new_chars: int


@dataclass(frozen=True)
class AppConfig:
    agent: AgentConfig
    policy: PolicyConfig
    sources: SourcesConfig
    output: OutputConfig
    state: StateConfig
    llm: LLMConfig


def _req(d: dict[str, Any], k: str) -> Any:
    if k not in d:
        raise KeyError(f"Missing config key: {k}")
    return d[k]


def load_config(path: Union[str, Path]) -> AppConfig:
    p = Path(path)
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))

    agent = _req(raw, "agent")
    policy = _req(raw, "policy")
    sources = _req(raw, "sources")
    output = _req(raw, "output")
    state = _req(raw, "state")
    llm = _req(raw, "llm")

    return AppConfig(
        agent=AgentConfig(
            name=str(_req(agent, "name")),
            user_agent=str(_req(agent, "user_agent")),
            max_pages_per_run=int(_req(agent, "max_pages_per_run")),
            max_chars_per_page=int(_req(agent, "max_chars_per_page")),
            request_timeout_s=int(_req(agent, "request_timeout_s")),
            delay_s=float(_req(agent, "delay_s")),
        ),
        policy=PolicyConfig(
            allow_http=bool(_req(policy, "allow_http")),
            obey_robots_txt=bool(_req(policy, "obey_robots_txt")),
            disallowed_domains=list(_req(policy, "disallowed_domains") or []),
        ),
        sources=SourcesConfig(
            feeds=list(_req(sources, "feeds") or []),
            seed_urls=list(_req(sources, "seed_urls") or []),
        ),
        output=OutputConfig(
            posts_dir=str(_req(output, "posts_dir")),
            timezone=str(_req(output, "timezone")),
            tags=list(_req(output, "tags") or []),
        ),
        state=StateConfig(path=str(_req(state, "path"))),
        llm=LLMConfig(
            kind=str(_req(llm, "kind")),
            checkpoint_path=str(_req(llm, "checkpoint_path")),
            vocab_text_path=str(_req(llm, "vocab_text_path")),
            temperature=float(_req(llm, "temperature")),
            max_new_chars=int(_req(llm, "max_new_chars")),
        ),
    )
