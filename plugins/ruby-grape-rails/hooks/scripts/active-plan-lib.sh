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
# 3. Fallback: most recent planning-phase plan (research exists, plan.md absent)
#
# Marker file lifecycle:
# - Written by: /rb:plan (after creating plan)
# - Cleared by: /rb:work (when all tasks complete)
# - Read by: session resume detection, precompact-rules.sh, log-progress.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
if [[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]]; then
  # shellcheck disable=SC1090,SC1091
  source "$ROOT_LIB"
fi
if ! declare -F library_safe_return >/dev/null 2>&1; then
  library_safe_return() {
    local status="${1:-0}"
    if [[ "${BASH_SOURCE[0]:-}" != "${0:-}" ]]; then
      return "$status"
    fi
    exit "$status"
  }
fi
if declare -F resolve_workspace_root >/dev/null 2>&1; then
  if [[ -n "${INPUT:-}" ]]; then
    REPO_ROOT=$(resolve_workspace_root "$INPUT") || REPO_ROOT=""
  else
    REPO_ROOT=$(resolve_workspace_root) || REPO_ROOT=""
  fi
else
  REPO_ROOT="${CLAUDE_PROJECT_DIR:-${PWD:-.}}"
fi
[[ -n "$REPO_ROOT" ]] || library_safe_return 0

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

get_planning_activity_mtime() {
  local plan_dir="$1"
  local newest_mtime=0
  local current_mtime
  local candidate

  if [[ -f "$plan_dir/scratchpad.md" && ! -L "$plan_dir/scratchpad.md" ]]; then
    current_mtime=$(get_file_mtime "$plan_dir/scratchpad.md" 2>/dev/null || echo 0)
    if [[ "$current_mtime" -gt "$newest_mtime" ]]; then
      newest_mtime="$current_mtime"
    fi
  fi

  if [[ -d "$plan_dir/research" && ! -L "$plan_dir/research" ]]; then
    while IFS= read -r -d '' candidate; do
      [[ ! -L "$candidate" ]] || continue
      current_mtime=$(get_file_mtime "$candidate" 2>/dev/null || echo 0)
      if [[ "$current_mtime" -gt "$newest_mtime" ]]; then
        newest_mtime="$current_mtime"
      fi
    done < <(find "$plan_dir/research" -type f -print0 2>/dev/null)

    if [[ "$newest_mtime" -eq 0 ]]; then
      newest_mtime=$(get_file_mtime "$plan_dir/research" 2>/dev/null || echo 0)
    fi
  fi

  printf '%s\n' "$newest_mtime"
}

# Get the active plan directory
# Returns: path to active plan directory, or empty if none
get_active_plan() {
  [[ ! -L "$CLAUDE_DIR" ]] || return 1

  # Primary: Check explicit marker file
  if [[ -f "$ACTIVE_PLAN_MARKER" ]]; then
    if [[ -L "$ACTIVE_PLAN_MARKER" ]]; then
      safe_remove_exact_file "$ACTIVE_PLAN_MARKER" "${CLAUDE_DIR}/ACTIVE_PLAN" || true
      return 1
    fi

    local marked_plan
    if ! IFS= read -r marked_plan < "$ACTIVE_PLAN_MARKER"; then
      safe_remove_exact_file "$ACTIVE_PLAN_MARKER" "${CLAUDE_DIR}/ACTIVE_PLAN" || true
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
    safe_remove_exact_file "$ACTIVE_PLAN_MARKER" "${CLAUDE_DIR}/ACTIVE_PLAN" || true
  fi
  
  # Fallback 1: Find most recent plan with unchecked tasks
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

  # Fallback 2: Find most recent planning-phase plan (research exists, plan.md absent)
  local newest_planning_dir=""
  local newest_planning_mtime=-1
  local plan_dir
  local planning_mtime

  if ! shopt -q nullglob; then
    shopt -s nullglob
    restore_nullglob=1
  fi

  for plan_dir in "${PLANS_DIR}"/*; do
    [[ -d "$plan_dir" ]] || continue
    [[ ! -L "$plan_dir" ]] || continue
    [[ -d "$plan_dir/research" ]] || continue
    [[ ! -f "$plan_dir/plan.md" ]] || continue

    planning_mtime=$(get_planning_activity_mtime "$plan_dir")
    if [[ "$planning_mtime" -gt "$newest_planning_mtime" ]]; then
      newest_planning_dir="$plan_dir"
      newest_planning_mtime="$planning_mtime"
    fi
  done

  if [[ "$restore_nullglob" -eq 1 ]]; then
    shopt -u nullglob
  fi

  if [[ -n "$newest_planning_dir" ]] && is_valid_plan_dir "$newest_planning_dir"; then
    printf '%s\n' "$newest_planning_dir"
    return 0
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

  [[ ! -L "$CLAUDE_DIR" ]] || return 1
  mkdir -p -- "$CLAUDE_DIR" || return 1
  [[ ! -L "$ACTIVE_PLAN_MARKER" ]] || return 1

  tmp_marker=$(mktemp "${CLAUDE_DIR}/ACTIVE_PLAN.XXXXXX") || return 1
  [[ -n "$tmp_marker" ]] || return 1
  [[ "$tmp_marker" == "${CLAUDE_DIR}/ACTIVE_PLAN."* ]] || return 1

  if ! (
    trap 'safe_remove_temp_file "${tmp_marker:-}" "'"${CLAUDE_DIR}"'/ACTIVE_PLAN.*" || true' EXIT HUP INT TERM
    printf '%s\n' "$plan_dir" > "$tmp_marker" &&
      mv -f -- "$tmp_marker" "$ACTIVE_PLAN_MARKER"
  ); then
    safe_remove_temp_file "$tmp_marker" "${CLAUDE_DIR}/ACTIVE_PLAN.*" || true
    return 1
  fi
}

# Clear the active plan marker (called on plan completion)
clear_active_plan() {
  [[ ! -L "$CLAUDE_DIR" ]] || return 1
  safe_remove_exact_file "$ACTIVE_PLAN_MARKER" "${CLAUDE_DIR}/ACTIVE_PLAN" || true
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
