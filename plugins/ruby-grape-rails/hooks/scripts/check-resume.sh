#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SessionStart hook: Detect plans with remaining tasks
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
INPUT=$(read_hook_input)
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0
PLANS_DIR="${REPO_ROOT}/.claude/plans"
SCRATCHPAD_LIB="${SCRIPT_DIR}/scratchpad-lib.sh"
[[ -r "$SCRATCHPAD_LIB" && ! -L "$SCRATCHPAD_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$SCRATCHPAD_LIB"

shopt -s nullglob
for dir in "${PLANS_DIR}"/*/; do
  [[ -d "$dir" && ! -L "$dir" ]] || continue
  [[ -f "${dir}plan.md" && ! -L "${dir}plan.md" ]] || continue
  UNCHECKED=$(grep -c -- '^\- \[ \]' "${dir}plan.md" 2>/dev/null || true)
  CHECKED=$(grep -cE -- '^\- \[[xX]\]' "${dir}plan.md" 2>/dev/null || true)
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
