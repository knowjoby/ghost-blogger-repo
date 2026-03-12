from __future__ import annotations

import re


_HAS_SENTIENCE_DISCLAIMER = re.compile(r"\bnot\s+sentient\b", re.IGNORECASE)


def validate_post_markdown(md: str, *, notes_count: int) -> list[str]:
    errors: list[str] = []
    text = (md or "").strip()

    if notes_count <= 0:
        errors.append("no notes collected")

    if len(text) < 250:
        errors.append("post too short")
    if len(text) > 80_000:
        errors.append("post too long")

    for required in ("## What I read", "## What I learned", "## My take"):
        if required not in text:
            errors.append(f"missing section: {required}")

    if notes_count > 0 and "Source: [" not in text:
        errors.append("missing source links")

    if not _HAS_SENTIENCE_DISCLAIMER.search(text):
        errors.append("missing 'not sentient' disclaimer in reflection")

    return errors
