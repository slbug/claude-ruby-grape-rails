#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SessionStart hook: Detect plans with remaining tasks
# Policy: advisory session-start reminder; degraded payload/root resolution
# should avoid blocking startup.
HOOK_NAME="${BASH_SOURCE[0]##*/}"

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: ${HOOK_NAME} cannot inspect the hook payload because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before continuing." >&2
  exit 2
}

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
    truncated|invalid)
      echo "BLOCKED: ${HOOK_NAME} could not safely inspect a ${HOOK_INPUT_STATUS} hook payload." >&2
      echo "Fix the hook input before retrying the session-start resume reminder." >&2
      exit 2
      ;;
  esac
fi
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0
PLANS_DIR="${REPO_ROOT}/.claude/plans"
SCRATCHPAD_LIB="${SCRIPT_DIR}/scratchpad-lib.sh"
[[ -r "$SCRATCHPAD_LIB" && ! -L "$SCRATCHPAD_LIB" ]] || emit_missing_dependency_block "scratchpad-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$SCRATCHPAD_LIB"

MARKDOWN_UNCHECKED_TASK_PATTERN='^[[:space:]]*(([-*+]|[0-9]+\.)[[:space:]]+)?\[ \]'
MARKDOWN_CHECKED_TASK_PATTERN='^[[:space:]]*(([-*+]|[0-9]+\.)[[:space:]]+)?\[[xX]\]'

shopt -s nullglob
for dir in "${PLANS_DIR}"/*/; do
  [[ -d "$dir" && ! -L "$dir" ]] || continue
  [[ -f "${dir}plan.md" && ! -L "${dir}plan.md" ]] || continue
  UNCHECKED=$(grep -cE -- "$MARKDOWN_UNCHECKED_TASK_PATTERN" "${dir}plan.md" 2>/dev/null || true)
  CHECKED=$(grep -cE -- "$MARKDOWN_CHECKED_TASK_PATTERN" "${dir}plan.md" 2>/dev/null || true)
  UNCHECKED=${UNCHECKED:-0}
  CHECKED=${CHECKED:-0}
  if [[ "$UNCHECKED" -gt 0 ]]; then
    SLUG="$(path_basename "$dir")"
    echo "↻ Plan '${SLUG}' has ${UNCHECKED} remaining tasks (${CHECKED} done). Resume with: /rb:work .claude/plans/${SLUG}/plan.md"
    SCRATCHPAD_FILE="${dir}scratchpad.md"
    if [[ -f "$SCRATCHPAD_FILE" && ! -L "$SCRATCHPAD_FILE" ]]; then
      DEAD_ENDS=$(count_dead_end_entries "$SCRATCHPAD_FILE")
      DEAD_ENDS=${DEAD_ENDS:-0}
      if [[ "$DEAD_ENDS" -gt 0 ]]; then
        echo "  ↳ Scratchpad has ${DEAD_ENDS} dead-end entr$( [[ "$DEAD_ENDS" -eq 1 ]] && printf 'y' || printf 'ies' ) — read .claude/plans/${SLUG}/scratchpad.md before retrying."
      fi
    fi
  fi
done
shopt -u nullglob
