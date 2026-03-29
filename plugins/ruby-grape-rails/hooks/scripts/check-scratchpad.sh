#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SessionStart hook: Surface existing scratchpads and dead-end-heavy
# plans before the user resumes work.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
# shellcheck disable=SC2034 # consumed by active-plan-lib during sourcing
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
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

  needs_scratchpad=false
  [[ "$plan_dir" == "$ACTIVE_PLAN" ]] && needs_scratchpad=true
  [[ -f "${plan_dir}/plan.md" && ! -L "${plan_dir}/plan.md" ]] && needs_scratchpad=true
  [[ -f "${plan_dir}/progress.md" && ! -L "${plan_dir}/progress.md" ]] && needs_scratchpad=true
  [[ -d "${plan_dir}/research" && ! -L "${plan_dir}/research" ]] && needs_scratchpad=true
  [[ "$needs_scratchpad" == "true" ]] || continue

  if [[ -f "${plan_dir}/scratchpad.md" && ! -L "${plan_dir}/scratchpad.md" ]]; then
    scratchpads+=("${plan_dir}/scratchpad.md")
  fi
done
shopt -u nullglob

COUNT=${#scratchpads[@]}

if [[ "$COUNT" -gt 0 ]]; then
  echo "Existing scratchpad notes found in $COUNT plan(s):"
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
