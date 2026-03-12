# Contributing

Thanks for helping improve Ghost Blogger.

## What to work on

- Reliability: fewer flaky runs, clearer logs, better fallbacks.
- Safety: stricter fetch policy, better robots compliance, better privacy redaction.
- Writing quality: clearer summaries, less repetition, better “reflective voice” prompts.

## Development

```bash
cd ghost_blogger_agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -e . --no-deps
pytest -q
```

## Pull requests

- Keep PRs small and focused.
- Add/adjust tests in `ghost_blogger_agent/tests/` when changing behavior.
- Do not add scraping features that require accounts, paywall bypass, or form submission.

