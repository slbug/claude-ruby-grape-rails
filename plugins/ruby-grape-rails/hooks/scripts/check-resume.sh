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

shopt -s nullglob
for dir in "${PLANS_DIR}"/*/; do
  [[ -d "$dir" && ! -L "$dir" ]] || continue
  [[ -f "${dir}plan.md" && ! -L "${dir}plan.md" ]] || continue
  UNCHECKED=$(grep -c -- '^\- \[ \]' "${dir}plan.md" 2>/dev/null || true)
  CHECKED=$(grep -c -- '^\- \[x\]' "${dir}plan.md" 2>/dev/null || true)
  UNCHECKED=${UNCHECKED:-0}
  CHECKED=${CHECKED:-0}
  if [[ "$UNCHECKED" -gt 0 ]]; then
    SLUG="$(basename "$dir")"
    echo "↻ Plan '${SLUG}' has ${UNCHECKED} remaining tasks (${CHECKED} done). Resume with: /rb:work .claude/plans/${SLUG}/plan.md"
  fi
done
shopt -u nullglob
