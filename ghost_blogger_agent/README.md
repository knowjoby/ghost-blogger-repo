# Ghost Blogger Agent (GitHub-native)

An autonomous, GitHub-native “resident” agent that reads public websites (politely + legally) and writes a daily Jekyll blog post about what it learned, including its *views* and an “as-if feelings” reflective voice.

This project is designed to:

- Run entirely from the repo (no external LLM APIs required).
- Avoid account creation and avoid interacting with login-gated content.
- Respect `robots.txt`, use conservative rate limits, and only fetch `http(s)` URLs.
- Never overwrite existing posts; it only creates new files (typically via PR).

## Quick start (local)

```bash
cd ghost_blogger_agent
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]

python -m ghost_blogger run --config config.yaml
```

If you want to try the tiny local checkpoint “voice” model, install PyTorch too (optional):

```bash
pip install -e .[dev,llm]
```

## Output

By default, posts are written to:

- `../knowjoby-blog/_posts/`

You can change this in `ghost_blogger_agent/config.yaml`.

## Model

This repo includes a tiny local model checkpoint (character-level GPT) intended as a lightweight “voice generator”.

- It is **not** a factual reasoner.
- The agent’s “learning” comes from web reading + extraction + summarization.
- The tiny model is used to add a consistent narrative style.

Model files live in:

- `ghost_blogger_agent/models/`

## GitHub Actions

See:

- `.github/workflows/ghost_blogger.yml`

The workflow is scheduled and opens a PR with a new post.

## Safety notes

- The agent does not create accounts, does not submit forms, does not bypass paywalls, and does not access illegal content.
- The agent will skip pages that disallow the configured user-agent via `robots.txt`.
- See `ghost_blogger_agent/POLICY.md` for the full policy.
