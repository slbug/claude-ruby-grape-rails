#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SessionStart hook: Detect plans with remaining tasks
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi
PLANS_DIR="${REPO_ROOT}/.claude/plans"

FOUND_PLAN=false
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
    FOUND_PLAN=true
  fi
done
shopt -u nullglob
if [[ "$FOUND_PLAN" == false ]]; then
  echo "Ruby/Rails/Grape plugin loaded"
fi
