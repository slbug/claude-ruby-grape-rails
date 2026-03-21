#!/usr/bin/env bash
# PreCompact hook: Detect active workflow phase and re-inject rules
# Uses explicit active-plan marker with fallback to heuristic detection

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/active-plan-lib.sh"

# Main detection
ACTIVE_PLAN_DIR=$(get_active_plan)
CONTEXT=""

if [[ -n "$ACTIVE_PLAN_DIR" ]]; then
  PLAN_SLUG=$(get_plan_slug "$ACTIVE_PLAN_DIR")
  PLAN_INTENT=$(get_plan_intent "$ACTIVE_PLAN_DIR")

  if is_full_mode "$ACTIVE_PLAN_DIR"; then
    CONTEXT="PRESERVE ACROSS COMPACTION — active /rb:full session:
"
    CONTEXT+="- Plan: ${PLAN_SLUG} — ${PLAN_INTENT}
"
    CONTEXT+="- Continue plan → work → verify → review → compound
"
    CONTEXT+="- Re-read progress.md and plan.md before resuming
"
  elif is_planning_phase "$ACTIVE_PLAN_DIR"; then
    CONTEXT="PRESERVE ACROSS COMPACTION — active /rb:plan session:
"
    CONTEXT+="- Plan: ${PLAN_SLUG} — ${PLAN_INTENT}
"
    CONTEXT+="- After writing plan.md you MUST STOP and present the plan
"
    CONTEXT+="- Never auto-start /rb:work
"
  else
    # Active work phase
    CONTEXT="PRESERVE ACROSS COMPACTION — active /rb:work session:
"
    CONTEXT+="- Plan: ${PLAN_SLUG} — ${PLAN_INTENT}
"
    CONTEXT+="- Re-read plan.md; checkboxes are the source of truth
"
    CONTEXT+="- Verify after each task using the project toolchain
"
    CONTEXT+="- Stop at blockers or when all tasks are complete
"
    CONTEXT+="- Never auto-start /rb:review
"
  fi
fi

if [[ -n "$CONTEXT" ]]; then
  printf '%b' "$CONTEXT" | jq -Rs '{systemMessage: .}'
fi
