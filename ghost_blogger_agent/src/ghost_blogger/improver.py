from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


def _data_dir(config_path: str) -> Path:
    cfg_path = Path(config_path).resolve()
    cfg = yaml.safe_load(cfg_path.read_text())
    posts_dir = (cfg_path.parent / cfg["output"]["posts_dir"]).resolve()
    return posts_dir.parent / "_data"


def improve_once(config_path: str) -> None:
    cfg_path = Path(config_path).resolve()
    cfg: dict[str, Any] = yaml.safe_load(cfg_path.read_text())
    data_dir = _data_dir(config_path)

    analysis_path = data_dir / "analysis.json"
    if not analysis_path.exists():
        print("[improver] analysis.json not found; skipping.")
        return

    analysis: dict[str, Any] = json.loads(analysis_path.read_text())

    improver_cfg = cfg.get("improver") or {}
    auto_add_seed_urls: bool = improver_cfg.get("auto_add_seed_urls", True)
    auto_remove_dead_feeds: bool = improver_cfg.get("auto_remove_dead_feeds", True)
    max_pages_delta: int = improver_cfg.get("max_pages_delta", 1)

    changes: list[str] = []
    new_cfg: dict[str, Any] = yaml.safe_load(cfg_path.read_text())  # fresh copy

    # 1. Remove dead feeds
    if auto_remove_dead_feeds:
        removes = analysis.get("suggested_feed_removes", [])
        existing_feeds: list[str] = new_cfg.get("sources", {}).get("feeds", [])
        removed = [f for f in removes if f in existing_feeds]
        if removed:
            new_cfg.setdefault("sources", {})["feeds"] = [f for f in existing_feeds if f not in removes]
            for f in removed:
                changes.append(f"removed dead feed: {f}")

    # 2. Add Wikipedia seed URLs for concept gaps
    if auto_add_seed_urls:
        new_seeds = analysis.get("suggested_seed_urls", [])
        existing_seeds: list[str] = new_cfg.get("sources", {}).get("seed_urls", [])
        added = [u for u in new_seeds if u not in existing_seeds]
        if added:
            new_cfg.setdefault("sources", {})["seed_urls"] = existing_seeds + added
            for u in added[:5]:  # cap additions per cycle
                changes.append(f"added seed url: {u}")

    # 3. Adjust max_pages_per_run based on success rate
    success_rate = analysis.get("run_success_rate_7d", 1.0)
    current_max = new_cfg.get("agent", {}).get("max_pages_per_run", 5)
    if success_rate < 0.5:
        new_max = max(3, current_max - max_pages_delta)
    elif success_rate > 0.8:
        new_max = min(15, current_max + max_pages_delta)
    else:
        new_max = current_max
    if new_max != current_max:
        new_cfg.setdefault("agent", {})["max_pages_per_run"] = new_max
        changes.append(f"max_pages_per_run: {current_max} → {new_max}")

    if not changes:
        print("[improver] no changes to apply.")
        _append_log(data_dir, success=True, changes=[], failure_reason=None)
        return

    # Write to temp file and dry-run validate
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".yaml")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            yaml.dump(new_cfg, f, default_flow_style=False, allow_unicode=True)

        result = subprocess.run(
            [sys.executable, "-m", "ghost_blogger", "run", "--config", tmp_path, "--dry-run"],
            capture_output=True,
            cwd=str(cfg_path.parent),
        )
        success = result.returncode == 0

        if success:
            cfg_path.write_text(
                yaml.dump(new_cfg, default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )
            print(f"[improver] applied {len(changes)} change(s): {changes}")
            _append_log(data_dir, success=True, changes=changes, failure_reason=None)
        else:
            failure_reason = result.stderr.decode("utf-8", errors="replace")[:500]
            print(f"[improver] dry-run failed; changes NOT applied. reason: {failure_reason}")
            _append_log(data_dir, success=False, changes=changes, failure_reason=failure_reason)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _append_log(data_dir: Path, *, success: bool, changes: list[str], failure_reason: str | None) -> None:
    log_path = data_dir / "improvement_log.json"
    log: list[dict] = []
    if log_path.exists():
        try:
            log = json.loads(log_path.read_text())
        except Exception:
            log = []
    log.append({
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "success": success,
        "changes": changes,
        "failure_reason": failure_reason,
    })
    log_path.write_text(json.dumps(log, indent=2), encoding="utf-8")
