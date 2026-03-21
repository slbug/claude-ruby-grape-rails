#!/usr/bin/env bash
# PostToolUse hook: Log file modifications to active progress file
# Uses explicit active-plan marker with fallback to heuristic detection

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/active-plan-lib.sh"

FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty')
[[ -n "$FILE_PATH" ]] || exit 0

ACTIVE_PLAN=$(get_active_plan)

if [[ -n "$ACTIVE_PLAN" && -d "$ACTIVE_PLAN" ]]; then
  PROGRESS_FILE="${ACTIVE_PLAN}/progress.md"
  echo "[$(date '+%H:%M')] Modified: $FILE_PATH" >> "$PROGRESS_FILE"
fi
