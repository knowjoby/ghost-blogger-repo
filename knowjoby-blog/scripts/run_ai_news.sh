#!/bin/bash
# Daily AI news runner — called by macOS LaunchAgent
# Uses Claude Code CLI (no separate API key needed)

BLOG_DIR="/Users/jobyjohn/github-blog"
CLAUDE_BIN="/Users/jobyjohn/.local/bin/claude"
LOG_FILE="$BLOG_DIR/logs/ai-news.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "" >> "$LOG_FILE"
echo "=== Run started: $DATE ===" >> "$LOG_FILE"

# Run Claude Code with the /ai-news command non-interactively
cd "$BLOG_DIR" || exit 1

"$CLAUDE_BIN" \
  --dangerously-skip-permissions \
  -p "/ai-news" \
  >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "=== Run finished: $(date '+%Y-%m-%d %H:%M:%S') (exit $EXIT_CODE) ===" >> "$LOG_FILE"
