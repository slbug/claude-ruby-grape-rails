#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SessionStart hook: Notify if scratchpad files exist from previous sessions
# Prioritizes active plan from marker, shows all plans with scratchpads

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
# shellcheck disable=SC2034 # consumed by active-plan-lib during sourcing
INPUT=$(read_hook_input)
LIB="${SCRIPT_DIR}/active-plan-lib.sh"
[[ -r "$LIB" && ! -L "$LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$LIB"

ACTIVE_PLAN=$(get_active_plan)
ACTIVE_SLUG=""
[[ -n "$ACTIVE_PLAN" ]] && ACTIVE_SLUG=$(get_plan_slug "$ACTIVE_PLAN")

scratchpads=()
if [[ -d "$PLANS_DIR" ]]; then
  while IFS= read -r -d '' file; do
    scratchpads+=("$file")
  done < <(find "$PLANS_DIR" -name "scratchpad.md" -type f -print0 2>/dev/null)
fi

COUNT=${#scratchpads[@]}

if [[ "$COUNT" -gt 0 ]]; then
  echo "Scratchpad notes found in $COUNT plan(s):"
  for file in "${scratchpads[@]}"; do
    [[ -f "$file" ]] || continue
    plan_dir=$(dirname "$file")
    plan_slug=$(basename "$plan_dir")
    
    # Mark active plan
    if [[ "$plan_slug" == "$ACTIVE_SLUG" ]]; then
      echo "  • $plan_slug (ACTIVE)"
    else
      echo "  • $plan_slug"
    fi
  done
fi
