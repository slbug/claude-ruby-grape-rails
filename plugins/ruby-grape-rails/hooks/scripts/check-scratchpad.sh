#!/usr/bin/env bash
# SessionStart hook: Notify if scratchpad files exist from previous sessions
# Prioritizes active plan from marker, shows all plans with scratchpads

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/active-plan-lib.sh"

ACTIVE_PLAN=$(get_active_plan)
ACTIVE_SLUG=""
[[ -n "$ACTIVE_PLAN" ]] && ACTIVE_SLUG=$(get_plan_slug "$ACTIVE_PLAN")

SCRATCHPADS=$(find .claude/plans -name "scratchpad.md" -type f 2>/dev/null)
COUNT=$(echo "$SCRATCHPADS" | grep -c . 2>/dev/null || echo "0")

if [[ "$COUNT" -gt 0 ]]; then
  echo "Scratchpad notes found in $COUNT plan(s):"
  echo "$SCRATCHPADS" | while read -r file; do
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
