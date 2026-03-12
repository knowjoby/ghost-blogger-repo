# Safety + permissions

This agent is intended to behave like a cautious web-reading researcher.

## Hard constraints

- Fetches only `http(s)` URLs.
- Does **not** create accounts.
- Does **not** submit forms or interact with authenticated flows.
- Does **not** bypass paywalls, CAPTCHAs, or access restrictions.
- Respects `robots.txt` for the configured user-agent (when enabled).
- Uses conservative rate limiting and timeouts.
- Writes **new** blog post files only; it does not overwrite existing posts.

## Scope

The default configuration focuses on public AI/ML research/news feeds. You can add feeds/seed URLs, but you should keep:

- legality: only public, lawful sources
- compliance: respect each site’s terms and robots directives
- privacy: avoid collecting personal data; the agent lightly redacts email/phone patterns in text

