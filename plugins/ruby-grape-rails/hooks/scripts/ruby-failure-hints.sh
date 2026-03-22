#!/usr/bin/env bash
set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0

COMMAND=$(jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
[[ -n "$COMMAND" ]] || exit 0

HINTS=""

if printf '%s' "$COMMAND" | grep -qE 'zeitwerk:check'; then
  HINTS="Zeitwerk failure hints:
- Check constant/file naming mismatches
- Confirm module nesting matches the path
- Read the first missing constant, not the cascade"
elif printf '%s' "$COMMAND" | grep -qE 'rubocop|standardrb'; then
  HINTS="Formatter/linter failure hints:
- Fix autocorrectable issues first
- Re-run on the narrowed file list before full-project runs
- Watch for stale Ruby target versions in config"
elif printf '%s' "$COMMAND" | grep -qE 'rspec|rails test'; then
  HINTS="Test failure hints:
- Re-run the single failing example or file first
- Check factories, transaction state, and time helpers
- Distinguish flaky integration failures from deterministic unit failures"
elif printf '%s' "$COMMAND" | grep -qE 'brakeman'; then
  HINTS="Brakeman failure hints:
- Separate real user-input flows from framework false positives
- Confirm sanitizer, policy, and strong-params coverage before suppressing"
elif printf '%s' "$COMMAND" | grep -qE 'db:migrate'; then
  HINTS="Migration failure hints:
- Check existing data against new constraints
- For indexes on large tables, prefer concurrent strategy where supported
- Re-read the first schema error, not the rollback noise"
fi

if [[ -n "$HINTS" ]]; then
  printf '%b' "$HINTS" | jq -Rs '{hookSpecificOutput: {hookEventName: "PostToolUseFailure", additionalContext: .}}'
fi
