from __future__ import annotations

from ghost_blogger.agent import GhostBloggerAgent
from ghost_blogger.config import load_config


def run_once(config_path: str) -> None:
    cfg = load_config(config_path)
    GhostBloggerAgent(cfg).run()

