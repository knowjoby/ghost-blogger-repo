# Ghost Blogger (agent + blog)

This repo contains:

- `ghost_blogger_agent/`: a safe web-reading agent that generates reflective Jekyll posts.
- `knowjoby-blog/`: the Jekyll blog that receives new posts in `knowjoby-blog/_posts/`.
- `.github/workflows/ghost_blogger.yml`: scheduled workflow that runs the agent and opens a PR with a new post.

## Local run

```bash
cd ghost_blogger_agent
python3 -m pip install -e '.[dev]'
python3 -m ghost_blogger run --config config.yaml
```

## GitHub Actions

The workflow runs on a schedule and creates a PR with the new post. You can also run it manually via “Run workflow”.

