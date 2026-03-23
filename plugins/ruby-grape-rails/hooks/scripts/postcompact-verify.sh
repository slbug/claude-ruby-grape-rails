#!/usr/bin/env bash
set -o nounset
set -o pipefail

# PostCompact hook: surface a recovery reminder after compaction.
# Uses stderr + exit 2 to advise Claude which workflow artifacts to re-read.

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

ACTIVE_PLAN_DIR=$(get_active_plan) || exit 0
[[ -n "$ACTIVE_PLAN_DIR" && -d "$ACTIVE_PLAN_DIR" ]] || exit 0

PLAN_SLUG=$(get_plan_slug "$ACTIVE_PLAN_DIR") || PLAN_SLUG=""
[[ -n "$PLAN_SLUG" ]] || exit 0

SCRATCHPAD_FILE="${ACTIVE_PLAN_DIR}/scratchpad.md"
PROGRESS_FILE="${ACTIVE_PLAN_DIR}/progress.md"

if is_planning_phase "$ACTIVE_PLAN_DIR"; then
  printf "POST-COMPACTION: Active /rb:plan state for '%s'. Re-read .claude/plans/%s/research/ and write plan.md before proceeding.\n" \
    "$PLAN_SLUG" "$PLAN_SLUG" >&2
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
