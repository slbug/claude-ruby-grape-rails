#!/usr/bin/env bash
set -o nounset
set -o pipefail

#
# Active Plan Detection Library
# Shared functions for determining which plan is currently active
#
# The active plan is determined by:
# 1. Explicit marker file (.claude/ACTIVE_PLAN) - primary
# 2. Fallback: most recently modified plan with unchecked tasks
#
# Marker file lifecycle:
# - Written by: /rb:plan (after creating plan)
# - Cleared by: /rb:work (when all tasks complete)
# - Read by: session resume detection, precompact-rules.sh, log-progress.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi

CLAUDE_DIR="${REPO_ROOT}/.claude"
PLANS_DIR="${CLAUDE_DIR}/plans"
ACTIVE_PLAN_MARKER="${CLAUDE_DIR}/ACTIVE_PLAN"

resolve_plan_dir() {
  local plan_dir="$1"
  [[ -n "$plan_dir" ]] || return 1

  if [[ "$plan_dir" == /* ]]; then
    printf '%s\n' "$plan_dir"
  else
    printf '%s\n' "${REPO_ROOT}/${plan_dir#./}"
  fi
}

is_valid_plan_dir() {
  local input_plan_dir="$1"
  local plan_dir

  [[ -n "$input_plan_dir" ]] || return 1
  [[ "$input_plan_dir" != *".."* ]] || return 1

  plan_dir=$(resolve_plan_dir "$input_plan_dir") || return 1
  [[ "$plan_dir" == "${PLANS_DIR}/"* ]] || return 1
  [[ -d "$plan_dir" ]] || return 1
  [[ ! -L "$plan_dir" ]] || return 1
}

get_file_mtime() {
  local file="$1"

  if stat -f '%m' "$file" >/dev/null 2>&1; then
    stat -f '%m' "$file"
  else
    stat -c '%Y' "$file"
  fi
}

# Get the active plan directory
# Returns: path to active plan directory, or empty if none
get_active_plan() {
  # Primary: Check explicit marker file
  if [[ -f "$ACTIVE_PLAN_MARKER" ]]; then
    if [[ -L "$ACTIVE_PLAN_MARKER" ]]; then
      rm -f -- "$ACTIVE_PLAN_MARKER"
      return 1
    fi

    local marked_plan
    if ! IFS= read -r marked_plan < "$ACTIVE_PLAN_MARKER"; then
      rm -f -- "$ACTIVE_PLAN_MARKER"
      return 1
    fi
    marked_plan=$(resolve_plan_dir "$marked_plan") || marked_plan=""

    # Validate: plan directory must exist
    if is_valid_plan_dir "$marked_plan"; then
      # Check if in planning phase (research exists, plan.md doesn't yet)
      if [[ -d "$marked_plan/research" && ! -f "$marked_plan/plan.md" ]]; then
        echo "$marked_plan"
        return 0
      fi

      # Check if plan.md exists with unchecked tasks (work phase)
      if [[ -f "$marked_plan/plan.md" ]] && grep -q '^\- \[ \]' "$marked_plan/plan.md" 2>/dev/null; then
        echo "$marked_plan"
        return 0
      fi
    fi

    # Marker is stale (plan completed or invalid), remove it
    rm -f -- "$ACTIVE_PLAN_MARKER"
  fi
  
  # Fallback: Find most recent plan with unchecked tasks
  local restore_nullglob=0
  local newest_plan=""
  local newest_mtime=-1
  local plan_file
  local plan_mtime

  if ! shopt -q nullglob; then
    shopt -s nullglob
    restore_nullglob=1
  fi

  for plan_file in "${PLANS_DIR}"/*/plan.md; do
    [[ -f "$plan_file" ]] || continue
    [[ ! -L "$plan_file" ]] || continue
    grep -q -- '^\- \[ \]' "$plan_file" 2>/dev/null || continue

    plan_mtime=$(get_file_mtime "$plan_file" 2>/dev/null || echo 0)
    if [[ "$plan_mtime" -gt "$newest_mtime" ]]; then
      newest_plan="$plan_file"
      newest_mtime="$plan_mtime"
    fi
  done

  if [[ "$restore_nullglob" -eq 1 ]]; then
    shopt -u nullglob
  fi

  if [[ -n "$newest_plan" ]]; then
    local newest_plan_dir
    newest_plan_dir="${newest_plan%/plan.md}"
    if is_valid_plan_dir "$newest_plan_dir"; then
      printf '%s\n' "$newest_plan_dir"
      return 0
    fi
  fi
  
  return 1
}

# Set the active plan marker
# Usage: set_active_plan /path/to/plans/slug
set_active_plan() {
  local input_plan_dir="$1"
  local plan_dir
  local tmp_marker

  is_valid_plan_dir "$input_plan_dir" || return 1
  plan_dir=$(resolve_plan_dir "$input_plan_dir") || return 1

  mkdir -p -- "$CLAUDE_DIR" || return 1
  [[ ! -L "$ACTIVE_PLAN_MARKER" ]] || return 1

  tmp_marker=$(mktemp "${CLAUDE_DIR}/ACTIVE_PLAN.XXXXXX") || return 1
  [[ -n "$tmp_marker" ]] || return 1
  trap 'rm -f -- "$tmp_marker"' EXIT HUP INT TERM

  printf '%s\n' "$plan_dir" > "$tmp_marker" || return 1
  mv -f -- "$tmp_marker" "$ACTIVE_PLAN_MARKER" || return 1
  trap - EXIT HUP INT TERM
}

# Clear the active plan marker (called on plan completion)
clear_active_plan() {
  rm -f -- "$ACTIVE_PLAN_MARKER"
}

# Check if a plan is in full mode (autonomous cycle)
# Usage: is_full_mode /path/to/plans/slug
is_full_mode() {
  local plan_dir="$1"
  [[ -n "$plan_dir" ]] || return 1
  
  local progress_file="${plan_dir}/progress.md"
  [[ -f "$progress_file" ]] && grep -q '\*\*State\*\*:' "$progress_file" 2>/dev/null
}

# Check if a plan is in planning phase
# Usage: is_planning_phase /path/to/plans/slug
is_planning_phase() {
  local plan_dir="$1"
  [[ -n "$plan_dir" ]] || return 1
  
  [[ -d "${plan_dir}/research" ]] && [[ ! -f "${plan_dir}/plan.md" ]]
}

# Get plan slug from directory
# Usage: get_plan_slug /path/to/plans/slug
get_plan_slug() {
  local plan_dir="$1"
  [[ -n "$plan_dir" ]] || return 1
  printf '%s\n' "${plan_dir##*/}"
}

# Get plan intent (first heading from plan.md)
# Usage: get_plan_intent /path/to/plans/slug
get_plan_intent() {
  local plan_dir="$1"
  [[ -n "$plan_dir" ]] || return 1
  
  local plan_file="${plan_dir}/plan.md"
  if [[ -f "$plan_file" ]]; then
    head -5 "$plan_file" 2>/dev/null | grep '^#' | head -1 | sed 's/^#* *//'
  fi
}
