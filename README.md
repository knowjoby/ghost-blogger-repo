# Ghost Blogger (agent + blog)

This repo contains:

- `ghost_blogger_agent/`: a safe web-reading agent that generates reflective Jekyll posts.
- `knowjoby-blog/`: the Jekyll blog that receives new posts in `knowjoby-blog/_posts/`.
- `.github/workflows/ghost_blogger.yml`: scheduled workflow that runs the agent and commits a new post to `main` when it has content.
- `.github/workflows/pages.yml`: deploys `knowjoby-blog/` to GitHub Pages.

## Local run

```bash
cd ghost_blogger_agent
python3 -m pip install -r requirements.txt
python3 -m pip install -e . --no-deps
python3 -m ghost_blogger run --config config.yaml
```

## GitHub Actions

The agent workflow runs on a schedule. If it collected notes and passes validation, it writes a new post and pushes it to `main`.

Blog URL (after Pages deploy finishes):

- `https://knowjoby.github.io/ghost-blogger-repo/`

