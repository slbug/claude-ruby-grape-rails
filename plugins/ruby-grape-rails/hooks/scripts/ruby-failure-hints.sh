#!/usr/bin/env bash
set -o nounset
set -o pipefail

HOOK_NAME="${BASH_SOURCE[0]##*/}"

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: ${HOOK_NAME} cannot inspect the hook payload because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before continuing." >&2
  exit 2
}

command -v jq >/dev/null 2>&1 || emit_missing_dependency_block "jq"
command -v grep >/dev/null 2>&1 || emit_missing_dependency_block "grep"

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
