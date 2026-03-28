#!/usr/bin/env bash
# Blocks dynamic context injection syntax (!`command`) in plugin/contributor docs.
# This feature executes shell commands at skill load time. The Ruby plugin does
# not use it and treats it as unsafe in tracked files.

set -euo pipefail

SCAN_TARGETS="plugins .claude README.md CLAUDE.md"
# shellcheck disable=SC2016
PATTERN='(^|[[:space:]\-:>])!\`[^`]+\`'
FOUND=0

for target in $SCAN_TARGETS; do
  if [[ ! -e "$target" ]]; then
    continue
  fi

  matches=$(
    grep -ERn --include='*.md' --include='*.json' "$PATTERN" "$target" 2>/dev/null || true
  )

  if [[ -n "$matches" ]]; then
    echo "BLOCKED: Dynamic context injection found:"
    echo "$matches"
    echo
    FOUND=1
  fi
done

if [[ "$FOUND" -eq 1 ]]; then
  echo "========================================="
  echo "ERROR: Dynamic context injection detected"
  echo "========================================="
  echo
  echo "The !\`command\` syntax executes shell commands and injects stdout into Claude context."
  echo "Do not use it in plugin files. Use normal tools/agents instead."
  exit 1
fi

echo "No dynamic context injection found."
