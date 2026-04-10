#!/usr/bin/env bash
# UserPromptSubmit hook: Auto-title sessions from /rb: commands.
# Only fires on the first prompt via "once": true in hooks.json.
# Uses hookSpecificOutput.sessionTitle (CC v2.1.94+).
# Policy: advisory — skips silently on missing deps or empty input.

set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0
command -v sed >/dev/null 2>&1 || exit 0
command -v head >/dev/null 2>&1 || exit 0
command -v cut >/dev/null 2>&1 || exit 0
command -v grep >/dev/null 2>&1 || exit 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"

read_hook_input
INPUT="$HOOK_INPUT_VALUE"
[[ -n "$INPUT" ]] || exit 0

PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // empty' 2>/dev/null)
[[ -n "$PROMPT" ]] || exit 0

# Use first line only — prompts can be multi-line
FIRST_LINE=$(printf '%s' "$PROMPT" | head -1)

# Match plugin skills: /rb:plan, /ruby-grape-rails:review
if [[ "$FIRST_LINE" =~ ^/(rb|ruby-grape-rails): ]]; then
  # Normalize: /ruby-grape-rails:review → /rb:review (strip full plugin prefix)
  NORMALIZED=$(printf '%s' "$FIRST_LINE" | sed -E 's|^/ruby-grape-rails:|/rb:|')

  # Extract command name: /rb:plan → rb:plan
  CMD=$(printf '%s' "$NORMALIZED" | grep -oE '^/[a-z]+:[a-z0-9-]+' | sed 's|^/||' || true)
  [[ -n "$CMD" ]] || exit 0

  # Extract args after command name, trim leading whitespace
  ARGS=$(printf '%s' "$FIRST_LINE" | sed -E "s|^/[a-z-]+:[a-z0-9-]+||" | sed 's|^ *||')

  # Clean up file paths: .claude/plans/auth-system/plan.md → auth-system
  if [[ "$ARGS" =~ \.claude/plans/([^/]+)/ ]]; then
    ARGS="${BASH_REMATCH[1]}"
  fi

  # Trim args to 60 chars at word boundary
  if [[ ${#ARGS} -gt 60 ]]; then
    ARGS=$(printf '%s' "$ARGS" | cut -c1-60 | sed 's/ [^ ]*$//')
  fi

  if [[ -n "$ARGS" ]]; then
    TITLE="${CMD} — ${ARGS}"
  else
    TITLE="${CMD}"
  fi

  jq -n --arg title "$TITLE" '{
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      sessionTitle: $title
    }
  }'
else
  # Non-plugin prompt — FIRST_LINE already extracted above

  # Skip if it's very short (likely a "yes", "no", continuation)
  [[ ${#FIRST_LINE} -gt 10 ]] || exit 0

  if [[ ${#FIRST_LINE} -gt 60 ]]; then
    FIRST_LINE=$(printf '%s' "$FIRST_LINE" | cut -c1-60 | sed 's/ [^ ]*$//')
  fi

  jq -n --arg title "$FIRST_LINE" '{
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      sessionTitle: $title
    }
  }'
fi
