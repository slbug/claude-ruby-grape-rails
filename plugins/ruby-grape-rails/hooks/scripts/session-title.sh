#!/usr/bin/env bash
# UserPromptSubmit hook: Auto-title sessions from /rb: commands.
# Fires only on first prompt via in-script per-session lock directory.
# Uses hookSpecificOutput.sessionTitle (CC v2.1.94+).
# Policy: advisory — skips silently on missing deps, empty input, or
# when the per-session lock already exists.

set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0
command -v sed >/dev/null 2>&1 || exit 0
command -v head >/dev/null 2>&1 || exit 0
command -v cut >/dev/null 2>&1 || exit 0
command -v grep >/dev/null 2>&1 || exit 0
command -v tr >/dev/null 2>&1 || exit 0

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

# Per-session lock: only title the first prompt of each session.
SESSION_ID=$(printf '%s' "$INPUT" | jq -r '.session_id // .sessionId // "default"' 2>/dev/null) || SESSION_ID="default"
SESSION_KEY=$(printf '%s' "$SESSION_ID" | tr -c '[:alnum:]_-' '_')
[[ -n "$SESSION_KEY" ]] || exit 0

LOCK_BASE="${CLAUDE_PLUGIN_DATA:-}"
if [[ -z "$LOCK_BASE" ]]; then
  REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
  [[ -n "$REPO_ROOT" ]] || exit 0
  CLAUDE_DIR="${REPO_ROOT}/.claude"
  [[ ! -L "$CLAUDE_DIR" ]] || exit 0
  mkdir -p -- "$CLAUDE_DIR" 2>/dev/null || exit 0
  [[ -d "$CLAUDE_DIR" && ! -L "$CLAUDE_DIR" ]] || exit 0
  HOOK_STATE_DIR="${CLAUDE_DIR}/.hook-state"
  [[ ! -L "$HOOK_STATE_DIR" ]] || exit 0
  mkdir -p -- "$HOOK_STATE_DIR" 2>/dev/null || exit 0
  [[ -d "$HOOK_STATE_DIR" && ! -L "$HOOK_STATE_DIR" ]] || exit 0
  LOCK_BASE="$HOOK_STATE_DIR"
fi
[[ ! -L "$LOCK_BASE" ]] || exit 0
LOCK_DIR="${LOCK_BASE}/session-titles"
[[ ! -L "$LOCK_DIR" ]] || exit 0
mkdir -p -- "$LOCK_DIR" 2>/dev/null || exit 0
[[ -d "$LOCK_DIR" && ! -L "$LOCK_DIR" ]] || exit 0

SESSION_LOCK="${LOCK_DIR}/${SESSION_KEY}"
[[ ! -L "$SESSION_LOCK" ]] || exit 0
# mkdir is atomic: exits non-zero if the lock already exists.
mkdir -- "$SESSION_LOCK" 2>/dev/null || exit 0

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
