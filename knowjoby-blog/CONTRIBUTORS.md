# Contributors

Thank you to everyone who has helped improve this AI news aggregator!

## Core Team
- [Your Name/Username] - Project maintainer

## Contributors

### DeepSeek AI
**Contributions:**
- Created centralized `config.py` as single source of truth for keywords and RSS feeds
- Implemented word-boundary regex matching (`\b`) to fix brittle keyword detection
- Expanded company keywords (Nvidia: "jensen huang", "h100", "blackwell"; Meta: fixed space issue; added DeepSeek, Perplexity, Stability AI)
- Added coverage bonus system (+8 for 2 sources, +15 for 3+ sources)
- Implemented source health tracking with `source_health.yml` and fallback age expansion
- Cleaned up dead code (`smart_fetcher.py`, `smart_scheduler.py`) and token budget fields
- Fixed breaking news monitor to handle correct data structures and log to `run_log.json`
- Added import path fixes for reliable script execution

## How to Contribute
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-improvement`)
3. Commit your changes (`git commit -m 'Add some amazing improvement'`)
4. Push to the branch (`git push origin feature/amazing-improvement`)
5. Open a Pull Request

## Recognition
All contributors will be added to this file. Thank you for helping make this project better!
