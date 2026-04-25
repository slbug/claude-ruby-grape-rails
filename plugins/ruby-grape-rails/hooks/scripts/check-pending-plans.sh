#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: advisory — warn/skip on degraded state, exit 0.


# Stop hook: Warn about plans with uncompleted tasks
# Guard against infinite loops per Claude Code docs
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
if [[ -z "$INPUT" ]]; then
  case "${HOOK_INPUT_STATUS:-empty}" in
  truncated | invalid)
    echo "BLOCKED: ${HOOK_NAME} could not safely inspect a ${HOOK_INPUT_STATUS} hook payload." >&2
    echo "Fix the hook input before retrying the stop-time plan reminder." >&2
    exit 2
    ;;
  esac
fi
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0
PLANS_DIR="${REPO_ROOT}/.claude/plans"

# Use the same pattern as active-plan-lib.sh to ensure consistency
MARKDOWN_UNCHECKED_TASK_PATTERN='^[[:space:]]*(([-*+]|[0-9]+\.)[[:space:]]+)?\[ \]'

PENDING=0
if [[ -d "$PLANS_DIR" ]]; then
  while IFS= read -r -d '' plan_file; do
    if grep -qE -- "$MARKDOWN_UNCHECKED_TASK_PATTERN" "$plan_file" 2>/dev/null; then
      PENDING=$((PENDING + 1))
    fi
  done < <(find "$PLANS_DIR" -name plan.md -type f -print0 2>/dev/null)
fi

if [[ "$PENDING" -gt 0 ]]; then
  echo "⚠ $PENDING plan(s) have uncompleted tasks"
fi
