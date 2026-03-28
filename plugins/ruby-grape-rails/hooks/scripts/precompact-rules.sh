#!/usr/bin/env bash
set -o nounset
set -o pipefail

# PreCompact hook: Detect active workflow phase and re-inject rules
# Uses explicit active-plan marker with fallback to heuristic detection

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
SCRATCHPAD_LIB="${SCRIPT_DIR}/scratchpad-lib.sh"
[[ -r "$SCRATCHPAD_LIB" && ! -L "$SCRATCHPAD_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$SCRATCHPAD_LIB"
command -v jq >/dev/null 2>&1 || exit 0

# Main detection
ACTIVE_PLAN_DIR=$(get_active_plan)
CONTEXT=""

if [[ -n "$ACTIVE_PLAN_DIR" ]]; then
  PLAN_SLUG=$(get_plan_slug "$ACTIVE_PLAN_DIR")
  PLAN_INTENT=$(get_plan_intent "$ACTIVE_PLAN_DIR")
  SCRATCHPAD_FILE="${ACTIVE_PLAN_DIR}/scratchpad.md"
  ensure_scratchpad_file "$ACTIVE_PLAN_DIR" "$PLAN_INTENT" || true

  if is_full_mode "$ACTIVE_PLAN_DIR"; then
    CONTEXT="PRESERVE ACROSS COMPACTION — active /rb:full session:
"
    CONTEXT+="- Plan: ${PLAN_SLUG} — ${PLAN_INTENT}
"
    CONTEXT+="- Continue plan → work → verify → review → compound
"
    CONTEXT+="- Re-read progress.md, plan.md, and scratchpad.md before resuming
"
  elif is_planning_phase "$ACTIVE_PLAN_DIR"; then
    CONTEXT="PRESERVE ACROSS COMPACTION — active /rb:plan session:
"
    CONTEXT+="- Plan: ${PLAN_SLUG} — ${PLAN_INTENT}
"
    CONTEXT+="- After writing plan.md you MUST STOP and present the plan
"
    CONTEXT+="- Preserve scratchpad decisions, hypotheses, and open questions
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
    CONTEXT+="- Re-read scratchpad.md for decisions, dead ends, and handoff context
"
    CONTEXT+="- Verify after each task using the project toolchain
"
    CONTEXT+="- Stop at blockers or when all tasks are complete
"
    CONTEXT+="- Never auto-start /rb:review
"
  fi

  if [[ -f "$SCRATCHPAD_FILE" && ! -L "$SCRATCHPAD_FILE" ]]; then
    DEAD_END_COUNT=$(count_dead_end_entries "$SCRATCHPAD_FILE")
    DEAD_END_COUNT=${DEAD_END_COUNT:-0}
    if [[ "$DEAD_END_COUNT" -gt 0 ]]; then
      DEAD_ENDS=$(extract_dead_end_section "$SCRATCHPAD_FILE" 2>/dev/null | sed '/^[[:space:]]*$/d' | head -20)
      if [[ -n "$DEAD_ENDS" ]]; then
        CONTEXT+="
SCRATCHPAD Dead Ends (${DEAD_END_COUNT}) — DO NOT RETRY:
${DEAD_ENDS}
"
      fi
    fi
  fi
fi

if [[ -n "$CONTEXT" ]]; then
  printf '%s' "$CONTEXT" | jq -Rs '{systemMessage: .}'
fi
