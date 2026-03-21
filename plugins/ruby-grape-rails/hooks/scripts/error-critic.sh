#!/usr/bin/env bash

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
ERROR=$(echo "$INPUT" | jq -r '.error // empty')

case "$COMMAND" in
  *"bundle exec rspec"*|*"rails test"*|*"zeitwerk:check"*|*"rubocop"*|*"standardrb"*|*"brakeman"*|*"db:migrate"*) ;;
  *) exit 0 ;;
esac

FAILURE_DIR="/tmp/.claude-ruby-failures"
mkdir -p "$FAILURE_DIR"
CMD_KEY=$(printf '%s' "$COMMAND" | tr -c '[:alnum:]' '_')
FAILURE_LOG="$FAILURE_DIR/${CMD_KEY}.log"
COUNT_FILE="$FAILURE_DIR/${CMD_KEY}.count"

if [[ -f "$COUNT_FILE" ]]; then
  COUNT=$(cat "$COUNT_FILE")
  COUNT=$((COUNT + 1))
else
  COUNT=1
fi
echo "$COUNT" > "$COUNT_FILE"

{
  echo "--- Failure #${COUNT} at $(date +%H:%M:%S) ---"
  echo "Command: $COMMAND"
  echo "$ERROR" | head -20
  echo
} >> "$FAILURE_LOG"

tail -100 "$FAILURE_LOG" > "$FAILURE_LOG.tmp" && mv "$FAILURE_LOG.tmp" "$FAILURE_LOG"

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
