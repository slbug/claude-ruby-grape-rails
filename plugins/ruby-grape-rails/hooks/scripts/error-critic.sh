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
INPUT="$HOOK_INPUT_VALUE"
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0
CLAUDE_DIR="${REPO_ROOT}/.claude"
HOOK_STATE_DIR="${CLAUDE_DIR}/.hook-state"
FAILURES_ROOT="${HOOK_STATE_DIR}/failures"

COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
ERROR=$(printf '%s' "$INPUT" | jq -r '.error // empty' 2>/dev/null) || ERROR=""
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // .sessionId // "default"' 2>/dev/null) || SESSION_ID="default"

case "$COMMAND" in
  *"bundle exec rspec"*|*"rails test"*|*"zeitwerk:check"*|*"rubocop"*|*"standardrb"*|*"brakeman"*|*"db:migrate"*) ;;
  *) exit 0 ;;
esac

emit_error_critic_temp_warning() {
  echo "WARNING: ${HOOK_NAME} skipped failure-loop analysis because a temporary file could not be created." >&2
  exit 0
}

emit_error_critic_state_warning() {
  echo "WARNING: ${HOOK_NAME} skipped failure-loop analysis because hook-state storage could not be prepared." >&2
  exit 0
}

emit_error_critic_write_warning() {
  echo "WARNING: ${HOOK_NAME} skipped failure-loop analysis because hook-state could not be updated." >&2
  exit 0
}

SESSION_KEY=$(printf '%s' "$SESSION_ID" | tr -c '[:alnum:]_-' '_')
CMD_KEY=$(printf '%s' "$COMMAND" | cksum | awk '{print $1}')
[[ ! -L "$CLAUDE_DIR" ]] || exit 0
mkdir -p -- "$CLAUDE_DIR" || emit_error_critic_state_warning
[[ -d "$CLAUDE_DIR" ]] || emit_error_critic_state_warning
[[ ! -L "$HOOK_STATE_DIR" ]] || exit 0
mkdir -p -- "$HOOK_STATE_DIR" || emit_error_critic_state_warning
[[ -d "$HOOK_STATE_DIR" ]] || emit_error_critic_state_warning
[[ ! -L "$FAILURES_ROOT" ]] || exit 0
mkdir -p -- "$FAILURES_ROOT" || emit_error_critic_state_warning
[[ -d "$FAILURES_ROOT" ]] || emit_error_critic_state_warning
FAILURE_DIR="${FAILURES_ROOT}/${SESSION_KEY}"
[[ ! -L "$FAILURE_DIR" ]] || exit 0
mkdir -p -- "$FAILURE_DIR" || emit_error_critic_state_warning
[[ -d "$FAILURE_DIR" && ! -L "$FAILURE_DIR" ]] || emit_error_critic_state_warning
FAILURE_LOG="$FAILURE_DIR/${CMD_KEY}.log"
COUNT_FILE="$FAILURE_DIR/${CMD_KEY}.count"
LOCK_DIR="$FAILURE_DIR/${CMD_KEY}.lock"
TRIMMED_LOG=""
TMP_COUNT=""
[[ ! -L "$FAILURE_LOG" ]] || exit 0
[[ ! -L "$COUNT_FILE" ]] || exit 0
[[ ! -e "$FAILURE_LOG" || -f "$FAILURE_LOG" ]] || exit 0
[[ ! -e "$COUNT_FILE" || -f "$COUNT_FILE" ]] || exit 0
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0
fi
cleanup_error_critic() {
  if [[ -n "$TRIMMED_LOG" ]]; then
    safe_remove_temp_file "$TRIMMED_LOG" "${FAILURE_DIR}/trimmed.*" 2>/dev/null || true
  fi
  if [[ -n "$TMP_COUNT" ]]; then
    safe_remove_temp_file "$TMP_COUNT" "${FAILURE_DIR}/count.*" 2>/dev/null || true
  fi
  rmdir -- "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup_error_critic EXIT HUP INT TERM

if [[ -f "$COUNT_FILE" ]]; then
  IFS= read -r COUNT < "$COUNT_FILE" || COUNT=0
  [[ "$COUNT" =~ ^[0-9]+$ ]] || COUNT=0
  COUNT=$((COUNT + 1))
else
  COUNT=1
fi
TMP_COUNT=$(mktemp "${FAILURE_DIR}/count.XXXXXX") || emit_error_critic_temp_warning
[[ -n "$TMP_COUNT" ]] || emit_error_critic_temp_warning
[[ "$TMP_COUNT" == "${FAILURE_DIR}/count."* ]] || emit_error_critic_temp_warning
printf '%s\n' "$COUNT" > "$TMP_COUNT" || emit_error_critic_write_warning
mv -f -- "$TMP_COUNT" "$COUNT_FILE" || emit_error_critic_write_warning
TMP_COUNT=""

{
  echo "--- Failure #${COUNT} at $(date +%H:%M:%S) ---"
  echo "Command: $COMMAND"
  printf '%s\n' "$ERROR" | head -20
  echo
} >> "$FAILURE_LOG"

TRIMMED_LOG=$(mktemp "${FAILURE_DIR}/trimmed.XXXXXX") || emit_error_critic_temp_warning
[[ -n "$TRIMMED_LOG" ]] || emit_error_critic_temp_warning
[[ "$TRIMMED_LOG" == "${FAILURE_DIR}/trimmed."* ]] || emit_error_critic_temp_warning
tail -100 "$FAILURE_LOG" > "$TRIMMED_LOG" || emit_error_critic_write_warning
mv -f -- "$TRIMMED_LOG" "$FAILURE_LOG" || emit_error_critic_write_warning
TRIMMED_LOG=""

if [[ "$COUNT" -lt 2 ]]; then
  exit 0
fi

if [[ "$COUNT" -eq 2 ]]; then
  HINT="REPEATED FAILURE (attempt #${COUNT}): this command already failed once. Stop retrying blindly. Re-read the first error and narrow the command before trying again. Consider /rb:investigate if the root cause is unclear."
  printf '%s' "$HINT" | jq -Rs '{hookSpecificOutput: {hookEventName: "PostToolUseFailure", additionalContext: .}}'
  exit 0
fi

ERROR_SUMMARY=$(grep -A2 'Failure #' "$FAILURE_LOG" 2>/dev/null | grep -v '^--$' | tail -30)
CRITIC_ANALYSIS="DEBUGGING LOOP DETECTED (attempt #${COUNT}).

${ERROR_SUMMARY}

Recovery:
1. Stop retrying the same fix.
2. Re-read the first failing command output.
3. Narrow the reproduction.
4. Fix the first real error, not the cascade.
5. Consider /rb:investigate if the failure pattern is still unclear."
printf '%s' "$CRITIC_ANALYSIS" | jq -Rs '{hookSpecificOutput: {hookEventName: "PostToolUseFailure", additionalContext: .}}'
