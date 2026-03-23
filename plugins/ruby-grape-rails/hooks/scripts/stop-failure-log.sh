#!/usr/bin/env bash
set -o nounset
set -o pipefail

# StopFailure hook: persist API-failure context to the active plan scratchpad.
# Output is ignored for StopFailure, so this hook focuses on durable resume state.

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

ACTIVE_PLAN_DIR=$(get_active_plan) || exit 0
[[ -n "$ACTIVE_PLAN_DIR" && -d "$ACTIVE_PLAN_DIR" ]] || exit 0

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

if mkdir "$LOCK_DIR" 2>/dev/null; then
  trap 'rmdir -- "$LOCK_DIR" 2>/dev/null || true' EXIT HUP INT TERM

  if [[ ! -e "$SCRATCHPAD_FILE" ]]; then
    : > "$SCRATCHPAD_FILE" || exit 0
  fi

  [[ -f "$SCRATCHPAD_FILE" && ! -L "$SCRATCHPAD_FILE" ]] || exit 0

  {
    printf '\n'
    printf '## API Failure — %s\n' "$(date '+%Y-%m-%d %H:%M')"
    printf '\n'
    printf "%s\n" "- Error type: \`$ERROR_TYPE\`"
    printf -- '- Last error: %s\n' "$ERROR_MESSAGE"
    printf "%s\n" "- Resume hint: re-read \`plan.md\`, \`scratchpad.md\`, and \`progress.md\`, then continue with \`/rb:work\`"
  } >> "$SCRATCHPAD_FILE"
fi

exit 0
