#!/bin/bash
# Run betterleaks scan on changed files to detect secrets
# This hook runs after file writes to check for accidentally committed secrets
#
# Hook input: JSON via stdin with .tool_input.file_path
# Exit 2 with stderr message to surface warning to Claude

set -e

# Parse hook input from stdin
FILE_PATH=""
if [ -t 0 ]; then
  # No stdin (shouldn't happen for PostToolUse), skip
  exit 0
else
  FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")
fi

# Check if betterleaks is available
if [ -z "$BETTERLEAKS_PATH" ] && command -v betterleaks &> /dev/null; then
  BETTERLEAKS_PATH=$(command -v betterleaks)
fi

if [ -z "$BETTERLEAKS_PATH" ]; then
  # Betterleaks not available, skip silently
  exit 0
fi

if [ -z "$FILE_PATH" ]; then
  # No specific file, check if we're in a git repo and scan last commit
  if git rev-parse --git-dir > /dev/null 2>&1; then
    # Scan the most recent changes
    TMP_DIR=$(mktemp -d)
    git diff HEAD~1 --name-only 2>/dev/null | head -20 | while read -r file; do
      if [ -f "$file" ]; then
        # Portable cp --parents alternative for macOS
        target_dir="$TMP_DIR/$(dirname "$file")"
        mkdir -p "$target_dir"
        cp "$file" "$target_dir/" 2>/dev/null || true
      fi
    done
    
    if [ -n "$(ls -A "$TMP_DIR" 2>/dev/null)" ]; then
      echo "🔒 Scanning recent changes for secrets..."
      "$BETTERLEAKS_PATH" dir "$TMP_DIR" --no-banner --redact=100 || true
    fi
    
    rm -rf "$TMP_DIR"
  fi
else
  # Scan specific file that was just written
  if [ -f "$FILE_PATH" ]; then
    # Quick scan on the single file
    RESULT=$($BETTERLEAKS_PATH dir "$FILE_PATH" --no-banner --redact=100 2>/dev/null || true)
    if [ -n "$RESULT" ]; then
      echo "⚠️  Potential secret detected in $FILE_PATH"
      echo "$RESULT"
      echo ""
      echo "To ignore: add '#betterleaks:allow' comment to the line"
      exit 2
    fi
  fi
fi

exit 0
