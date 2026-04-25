#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: advisory — warn/skip on degraded state, exit 0.


# StopFailure hook: persist API-failure context to the active plan scratchpad.
# Output is ignored for StopFailure, so this hook focuses on durable resume state.

HOOK_NAME="${BASH_SOURCE[0]##*/}"

emit_missing_dependency_notice() {
  local dependency="$1"

  echo "WARNING: ${HOOK_NAME} cannot persist stop-failure context because ${dependency} is unavailable." >&2
  exit 0
}

command -v grep >/dev/null 2>&1 || emit_missing_dependency_notice "grep"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_notice "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
if [[ -z "$INPUT" ]]; then
  case "${HOOK_INPUT_STATUS:-empty}" in
    truncated|invalid)
      echo "WARNING: ${HOOK_NAME} could not safely inspect a ${HOOK_INPUT_STATUS} hook payload." >&2
      append_hook_degradation_log "$HOOK_NAME" "stop-failure context was not persisted because hook input was ${HOOK_INPUT_STATUS}" "$INPUT" || true
      exit 0
      ;;
  esac
fi

LIB="${SCRIPT_DIR}/active-plan-lib.sh"
[[ -r "$LIB" && ! -L "$LIB" ]] || emit_missing_dependency_notice "active-plan-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$LIB"
SCRATCHPAD_LIB="${SCRIPT_DIR}/scratchpad-lib.sh"
[[ -r "$SCRATCHPAD_LIB" && ! -L "$SCRATCHPAD_LIB" ]] || emit_missing_dependency_notice "scratchpad-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$SCRATCHPAD_LIB"

ACTIVE_PLAN_DIR=$(get_active_plan) || exit 0
[[ -n "$ACTIVE_PLAN_DIR" && -d "$ACTIVE_PLAN_DIR" ]] || exit 0

PLANNING_PHASE=false
if is_planning_phase "$ACTIVE_PLAN_DIR"; then
  PLANNING_PHASE=true
fi

SCRATCHPAD_FILE="${ACTIVE_PLAN_DIR}/scratchpad.md"
LOCK_DIR="${ACTIVE_PLAN_DIR}/.stop-failure.lock"

[[ ! -L "$SCRATCHPAD_FILE" ]] || exit 0
[[ ! -L "$LOCK_DIR" ]] || exit 0
[[ ! -e "$SCRATCHPAD_FILE" || -f "$SCRATCHPAD_FILE" ]] || exit 0

ERROR_TYPE="unknown"
ERROR_MESSAGE="Turn ended due to API error."

normalize_error_message() {
  local message="${1-}"

  message="${message//$'\r'/ }"
  message="${message//$'\n'/ }"
  message=$(printf '%s' "$message" | tr -s '[:space:]' ' ')
  message="${message#"${message%%[![:space:]]*}"}"
  message="${message%"${message##*[![:space:]]}"}"

  if [[ ${#message} -gt 300 ]]; then
    message="${message:0:297}..."
  fi

  printf '%s\n' "$message"
}

normalize_error_type() {
  local value="${1-}"

  value="${value//$'\r'/ }"
  value="${value//$'\n'/ }"
  value=$(printf '%s' "$value" | tr -s '[:space:]' ' ')
  value="${value#"${value%%[![:space:]]*}"}"
  value="${value%"${value##*[![:space:]]}"}"
  value="${value//\`/}"

  if [[ ${#value} -gt 80 ]]; then
    value="${value:0:77}..."
  fi

  printf '%s\n' "$value"
}

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

if command -v jq >/dev/null 2>&1; then
  ERROR_TYPE=$(printf '%s' "$INPUT" | jq -r '.error // empty' 2>/dev/null) || ERROR_TYPE="unknown"
  ERROR_MESSAGE=$(printf '%s' "$INPUT" | jq -r '.last_assistant_message // empty' 2>/dev/null) || ERROR_MESSAGE=""
fi

[[ -n "$ERROR_TYPE" ]] || ERROR_TYPE="unknown"
[[ -n "$ERROR_MESSAGE" ]] || ERROR_MESSAGE="Turn ended due to API error."
ERROR_TYPE=$(normalize_error_type "$ERROR_TYPE")
ERROR_MESSAGE=$(normalize_error_message "$ERROR_MESSAGE")
[[ -n "$ERROR_TYPE" ]] || ERROR_TYPE="unknown"
[[ -n "$ERROR_MESSAGE" ]] || ERROR_MESSAGE="Turn ended due to API error."

RESUME_HINT="re-read \`plan.md\`, \`scratchpad.md\`, and \`progress.md\`, then continue with \`/rb:work\`"
if [[ "$PLANNING_PHASE" == "true" ]]; then
  RESUME_HINT="re-read \`research/\` and \`scratchpad.md\`, finish synthesizing \`plan.md\`, then continue with \`/rb:plan\`"
fi

clear_stale_lock "$LOCK_DIR"
if mkdir "$LOCK_DIR" 2>/dev/null; then
  trap 'rmdir -- "$LOCK_DIR" 2>/dev/null || true' EXIT HUP INT TERM

  ensure_scratchpad_file "$ACTIVE_PLAN_DIR" "$(get_plan_intent "$ACTIVE_PLAN_DIR" 2>/dev/null || true)" || exit 0
  [[ -f "$SCRATCHPAD_FILE" && ! -L "$SCRATCHPAD_FILE" ]] || exit 0

  NOTE=$(cat <<EOF
### $(date '+%Y-%m-%d %H:%M') API Failure
- Error type: \`$ERROR_TYPE\`
- Error message: $ERROR_MESSAGE
- Resume hint: $RESUME_HINT
EOF
)
  append_handoff_note "$SCRATCHPAD_FILE" "$NOTE" || exit 0
fi

exit 0
