from __future__ import annotations

from ghost_blogger.agent import GhostBloggerAgent
from ghost_blogger.config import load_config


def run_once(config_path: str, *, dry_run: bool = False) -> None:
    cfg = load_config(config_path)
    GhostBloggerAgent(cfg, dry_run=dry_run).run()

