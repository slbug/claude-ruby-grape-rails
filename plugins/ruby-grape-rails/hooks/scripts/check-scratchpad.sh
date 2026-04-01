#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SessionStart hook: Surface existing scratchpads, auto-initialize missing
# scratchpads for active/resumable plans, and highlight dead-end-heavy plans.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
# shellcheck disable=SC2034 # consumed by active-plan-lib during sourcing
INPUT="$HOOK_INPUT_VALUE"
case "${HOOK_INPUT_STATUS:-empty}" in
  truncated|invalid)
    echo "Warning: skipping check-scratchpad.sh because hook input was ${HOOK_INPUT_STATUS}" >&2
    exit 0
    ;;
esac
LIB="${SCRIPT_DIR}/active-plan-lib.sh"
[[ -r "$LIB" && ! -L "$LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$LIB"
SCRATCHPAD_LIB="${SCRIPT_DIR}/scratchpad-lib.sh"
[[ -r "$SCRATCHPAD_LIB" && ! -L "$SCRATCHPAD_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$SCRATCHPAD_LIB"

ACTIVE_PLAN=$(get_active_plan)
ACTIVE_SLUG=""
[[ -n "$ACTIVE_PLAN" ]] && ACTIVE_SLUG=$(get_plan_slug "$ACTIVE_PLAN")

scratchpads=()
shopt -s nullglob
for plan_dir in "${PLANS_DIR}"/*; do
  [[ -d "$plan_dir" && ! -L "$plan_dir" ]] || continue
  scratchpad_file="${plan_dir}/scratchpad.md"

  needs_scratchpad=false
  if [[ "$plan_dir" == "$ACTIVE_PLAN" ]]; then
    needs_scratchpad=true
  elif plan_has_unchecked_tasks "${plan_dir}/plan.md"; then
    needs_scratchpad=true
  elif [[ -d "${plan_dir}/research" && ! -L "${plan_dir}/research" && ! -f "${plan_dir}/plan.md" ]]; then
    needs_scratchpad=true
  fi

  if [[ "$needs_scratchpad" == "true" ]]; then
    ensure_scratchpad_file "$plan_dir" "$(get_plan_intent "$plan_dir" 2>/dev/null || true)" || true
  fi

  if [[ -f "$scratchpad_file" && ! -L "$scratchpad_file" ]]; then
    scratchpads+=("$scratchpad_file")
  fi
done
shopt -u nullglob

COUNT=${#scratchpads[@]}

if [[ "$COUNT" -gt 0 ]]; then
  echo "Scratchpad notes ready in $COUNT plan(s):"
  for file in "${scratchpads[@]}"; do
    [[ -f "$file" ]] || continue
    plan_dir=$(path_dirname "$file")
    plan_slug=$(path_basename "$plan_dir")
    dead_end_count=$(count_dead_end_entries "$file")
    marker=""

    if [[ "$plan_slug" == "$ACTIVE_SLUG" ]]; then
      marker="ACTIVE"
    fi
    if [[ "$dead_end_count" -gt 0 ]]; then
      if [[ -n "$marker" ]]; then
        marker+=", "
      fi
      marker+="${dead_end_count} dead-end entries — READ BEFORE RETRYING"
    fi

    if [[ -n "$marker" ]]; then
      echo "  • $plan_slug (${marker})"
    else
      echo "  • $plan_slug"
    fi
  done
fi
