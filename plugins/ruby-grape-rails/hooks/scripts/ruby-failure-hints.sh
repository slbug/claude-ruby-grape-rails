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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
case "${HOOK_INPUT_STATUS:-ok}" in
  invalid)
    echo "BLOCKED: ${HOOK_NAME} could not safely inspect an invalid hook payload." >&2
    exit 2
    ;;
  truncated)
    echo "BLOCKED: ${HOOK_NAME} could not safely inspect a truncated hook payload." >&2
    exit 2
    ;;
esac
INPUT="$HOOK_INPUT_VALUE"

COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
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
