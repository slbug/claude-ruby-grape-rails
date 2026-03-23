#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Stop hook: Warn about plans with uncompleted tasks
# Guard against infinite loops per Claude Code docs
command -v jq >/dev/null 2>&1 || exit 0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
INPUT=$(read_hook_input)
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0
PLANS_DIR="${REPO_ROOT}/.claude/plans"

if [[ "$(printf '%s' "$INPUT" | jq -r '.stop_hook_active // empty' 2>/dev/null)" == "true" ]]; then
  exit 0
fi

PENDING=0
if [[ -d "$PLANS_DIR" ]]; then
  while IFS= read -r -d '' plan_file; do
    if grep -q -- '\[ \]' "$plan_file" 2>/dev/null; then
      PENDING=$((PENDING + 1))
    fi
  done < <(find "$PLANS_DIR" -name plan.md -type f -print0 2>/dev/null)
fi

if [[ "$PENDING" -gt 0 ]]; then
  echo "⚠ $PENDING plan(s) have uncompleted tasks"
fi
