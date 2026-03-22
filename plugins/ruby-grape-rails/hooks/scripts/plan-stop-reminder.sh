#!/usr/bin/env bash
set -o nounset
set -o pipefail

# PostToolUse hook: When a plan.md file is CREATED (Write, not Edit),
# remind Claude to STOP and present the plan to the user.
# Skips in /rb:full autonomous mode (detected by progress.md with State).

command -v jq >/dev/null 2>&1 || exit 0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi
PLANS_DIR="${REPO_ROOT}/.claude/plans"

INPUT=$(cat)
FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[[ -n "$FILE_PATH" ]] || exit 0

if [[ "$FILE_PATH" != /* ]]; then
  FILE_PATH="${REPO_ROOT}/${FILE_PATH#./}"
fi

# Only trigger for plan.md files
case "$FILE_PATH" in
  "${PLANS_DIR}"/*/plan.md) ;;
  *) exit 0 ;;
esac
[[ -f "$FILE_PATH" && ! -L "$FILE_PATH" ]] || exit 0

# Only trigger on Write (new plan creation), not Edit (checkbox updates).
# Write tool has .tool_input.content; Edit tool has .tool_input.old_string.
CONTENT=$(printf '%s' "$INPUT" | jq -r '.tool_input.content // empty' 2>/dev/null) || exit 0
[[ -n "$CONTENT" ]] || exit 0

# Skip in /rb:full autonomous mode — workflow-orchestrator creates
# progress.md with **State**: field during INITIALIZING.
PLAN_DIR="${FILE_PATH%/*}"
if [[ -f "${PLAN_DIR}/progress.md" && ! -L "${PLAN_DIR}/progress.md" ]] && grep -q '\*\*State\*\*:' "${PLAN_DIR}/progress.md" 2>/dev/null; then
  exit 0
fi

# PostToolUse: exit 2 + stderr feeds message to Claude (stdout is verbose-mode only)
cat >&2 <<'MSG'

==========================================
STOP: Plan file created.
==========================================
Do NOT proceed to implementation.
Present a brief summary of the plan to the user,
then use AskUserQuestion with options:
  - Start in fresh session (recommended)
  - Start here
  - Review the plan
  - Adjust the plan
==========================================
MSG
exit 2
