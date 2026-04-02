#!/usr/bin/env bash
set -o nounset
set -o pipefail

# PostCompact hook: surface a recovery reminder after compaction.
# Uses stderr + exit 2 to advise Claude which workflow artifacts to re-read.

HOOK_NAME="${BASH_SOURCE[0]##*/}"

emit_missing_dependency_notice() {
  local dependency="$1"

  echo "WARNING: ${HOOK_NAME} cannot prepare the post-compaction reminder because ${dependency} is unavailable." >&2
  exit 0
}

command -v grep >/dev/null 2>&1 || emit_missing_dependency_notice "grep"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_notice "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
# shellcheck disable=SC2034 # consumed by active-plan-lib during sourcing
read_hook_input
# shellcheck disable=SC2034 # consumed by active-plan-lib during sourcing
INPUT="$HOOK_INPUT_VALUE"

LIB="${SCRIPT_DIR}/active-plan-lib.sh"
[[ -r "$LIB" && ! -L "$LIB" ]] || emit_missing_dependency_notice "active-plan-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$LIB"

ACTIVE_PLAN_DIR=$(get_active_plan) || exit 0
[[ -n "$ACTIVE_PLAN_DIR" && -d "$ACTIVE_PLAN_DIR" ]] || exit 0

PLAN_SLUG=$(get_plan_slug "$ACTIVE_PLAN_DIR") || PLAN_SLUG=""
[[ -n "$PLAN_SLUG" ]] || exit 0

SCRATCHPAD_FILE="${ACTIVE_PLAN_DIR}/scratchpad.md"
PROGRESS_FILE="${ACTIVE_PLAN_DIR}/progress.md"

if is_planning_phase "$ACTIVE_PLAN_DIR"; then
  MESSAGE="POST-COMPACTION: Active /rb:plan state for '${PLAN_SLUG}'. Re-read .claude/plans/${PLAN_SLUG}/research/"
  if [[ -f "$SCRATCHPAD_FILE" && ! -L "$SCRATCHPAD_FILE" ]]; then
    MESSAGE+=", .claude/plans/${PLAN_SLUG}/scratchpad.md"
  fi
  MESSAGE+=" and write plan.md before proceeding."
  printf '%s\n' "$MESSAGE" >&2
  exit 2
fi

MESSAGE="POST-COMPACTION: Active plan '${PLAN_SLUG}' detected. Re-read .claude/plans/${PLAN_SLUG}/plan.md"

if [[ -f "$SCRATCHPAD_FILE" && ! -L "$SCRATCHPAD_FILE" ]]; then
  MESSAGE+=", .claude/plans/${PLAN_SLUG}/scratchpad.md"
fi

if [[ -f "$PROGRESS_FILE" && ! -L "$PROGRESS_FILE" ]]; then
  MESSAGE+=", and .claude/plans/${PLAN_SLUG}/progress.md"
fi

MESSAGE+=" before resuming."

printf '%s\n' "$MESSAGE" >&2
exit 2
