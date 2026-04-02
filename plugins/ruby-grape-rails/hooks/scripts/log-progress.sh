#!/usr/bin/env bash
set -o nounset
set -o pipefail

# PostToolUse hook: Log file modifications to active progress file
# Uses explicit active-plan marker with fallback to heuristic detection
# Policy: advisory observability hook; degraded payloads warn/skip instead of
# blocking the edit itself.

HOOK_NAME="${BASH_SOURCE[0]##*/}"

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: ${HOOK_NAME} cannot inspect the hook payload because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before continuing." >&2
  exit 2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
case "${HOOK_INPUT_STATUS:-empty}" in
  invalid)
    echo "WARNING: ${HOOK_NAME} skipped progress logging because the hook payload was invalid." >&2
    exit 0
    ;;
  truncated)
    echo "WARNING: ${HOOK_NAME} skipped progress logging because the hook payload was truncated." >&2
    exit 0
    ;;
esac
LIB="${SCRIPT_DIR}/active-plan-lib.sh"
[[ -r "$LIB" && ! -L "$LIB" ]] || emit_missing_dependency_block "active-plan-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$LIB"

command -v jq >/dev/null 2>&1 || emit_missing_dependency_block "jq"
command -v grep >/dev/null 2>&1 || emit_missing_dependency_block "grep"

clear_stale_lock() {
  local lock_dir="$1"
  local now
  local lock_mtime

  [[ -d "$lock_dir" && ! -L "$lock_dir" ]] || return 0
  now=$(date +%s 2>/dev/null || echo 0)
  lock_mtime=$(get_file_mtime "$lock_dir" 2>/dev/null || echo 0)
  [[ "$now" -gt 0 && "$lock_mtime" -gt 0 ]] || return 0

  if (( now - lock_mtime > 600 )); then
    rmdir -- "$lock_dir" 2>/dev/null || true
  fi
}

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
  clear_stale_lock "$PROGRESS_LOCK_DIR"
  if mkdir "$PROGRESS_LOCK_DIR" 2>/dev/null; then
    cleanup_log_progress() {
      rmdir -- "$PROGRESS_LOCK_DIR" 2>/dev/null || true
    }
    trap cleanup_log_progress EXIT HUP INT TERM
    printf '[%s] Modified: %s\n' "$(date '+%H:%M')" "$LOGGED_PATH" >> "$PROGRESS_FILE"
  fi
fi
