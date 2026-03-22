#!/usr/bin/env bash
set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi

INPUT=$(cat)
COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
ERROR=$(printf '%s' "$INPUT" | jq -r '.error // empty' 2>/dev/null) || ERROR=""
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // .sessionId // "default"' 2>/dev/null) || SESSION_ID="default"

case "$COMMAND" in
  *"bundle exec rspec"*|*"rails test"*|*"zeitwerk:check"*|*"rubocop"*|*"standardrb"*|*"brakeman"*|*"db:migrate"*) ;;
  *) exit 0 ;;
esac

SESSION_KEY=$(printf '%s' "$SESSION_ID" | tr -c '[:alnum:]_-' '_')
CMD_KEY=$(printf '%s' "$COMMAND" | cksum | awk '{print $1}')
FAILURE_DIR="${REPO_ROOT}/.claude/.hook-state/failures/${SESSION_KEY}"
mkdir -p -- "$FAILURE_DIR" || exit 0
[[ -d "$FAILURE_DIR" && ! -L "$FAILURE_DIR" ]] || exit 0
FAILURE_LOG="$FAILURE_DIR/${CMD_KEY}.log"
COUNT_FILE="$FAILURE_DIR/${CMD_KEY}.count"
LOCK_DIR="$FAILURE_DIR/${CMD_KEY}.lock"
TRIMMED_LOG=""
[[ ! -L "$FAILURE_LOG" ]] || exit 0
[[ ! -L "$COUNT_FILE" ]] || exit 0
[[ ! -e "$FAILURE_LOG" || -f "$FAILURE_LOG" ]] || exit 0
[[ ! -e "$COUNT_FILE" || -f "$COUNT_FILE" ]] || exit 0
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0
fi
cleanup_error_critic() {
  [[ -n "$TRIMMED_LOG" ]] && rm -f -- "$TRIMMED_LOG" 2>/dev/null || true
  rmdir -- "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup_error_critic EXIT HUP INT TERM

if [[ -f "$COUNT_FILE" ]]; then
  COUNT=$(cat -- "$COUNT_FILE")
  [[ "$COUNT" =~ ^[0-9]+$ ]] || COUNT=0
  COUNT=$((COUNT + 1))
else
  COUNT=1
fi
echo "$COUNT" > "$COUNT_FILE"

{
  echo "--- Failure #${COUNT} at $(date +%H:%M:%S) ---"
  echo "Command: $COMMAND"
  printf '%s\n' "$ERROR" | head -20
  echo
} >> "$FAILURE_LOG"

TRIMMED_LOG=$(mktemp "${FAILURE_DIR}/trimmed.XXXXXX") || exit 0
[[ -n "$TRIMMED_LOG" ]] || exit 0
tail -100 "$FAILURE_LOG" > "$TRIMMED_LOG" && mv -f -- "$TRIMMED_LOG" "$FAILURE_LOG"
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
printf '%b' "$CRITIC_ANALYSIS" | jq -Rs '{hookSpecificOutput: {hookEventName: "PostToolUseFailure", additionalContext: .}}'
