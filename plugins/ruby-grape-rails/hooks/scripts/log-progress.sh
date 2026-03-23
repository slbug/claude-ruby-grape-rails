#!/usr/bin/env bash
set -o nounset
set -o pipefail

# PostToolUse hook: Log file modifications to active progress file
# Uses explicit active-plan marker with fallback to heuristic detection

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
INPUT=$(read_hook_input)
LIB="${SCRIPT_DIR}/active-plan-lib.sh"
[[ -r "$LIB" && ! -L "$LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$LIB"

command -v jq >/dev/null 2>&1 || exit 0

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[[ -n "$FILE_PATH" ]] || exit 0

ACTIVE_PLAN=$(get_active_plan)

if [[ -n "$ACTIVE_PLAN" && -d "$ACTIVE_PLAN" ]]; then
  PROGRESS_FILE="${ACTIVE_PLAN}/progress.md"
  PROGRESS_LOCK_DIR="${ACTIVE_PLAN}/.progress.lock"
  [[ ! -L "$PROGRESS_FILE" ]] || exit 0
  [[ ! -L "$PROGRESS_LOCK_DIR" ]] || exit 0
  [[ ! -e "$PROGRESS_FILE" || -f "$PROGRESS_FILE" ]] || exit 0
  printf -v LOGGED_PATH '%q' "$FILE_PATH"
  if mkdir "$PROGRESS_LOCK_DIR" 2>/dev/null; then
    cleanup_log_progress() {
      rmdir -- "$PROGRESS_LOCK_DIR" 2>/dev/null || true
    }
    trap cleanup_log_progress EXIT HUP INT TERM
    printf '[%s] Modified: %s\n' "$(date '+%H:%M')" "$LOGGED_PATH" >> "$PROGRESS_FILE"
  fi
fi
