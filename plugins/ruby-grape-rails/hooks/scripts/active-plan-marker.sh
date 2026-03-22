#!/usr/bin/env bash
set -e
set -o nounset
set -o pipefail

#
# Active Plan Marker Management
# 
# This script manages the .claude/ACTIVE_PLAN marker file that tracks
# which plan is currently active across the workflow lifecycle.
#
# Usage:
#   active-plan-marker.sh set <plan-directory>   # Set active plan
#   active-plan-marker.sh clear                  # Clear marker (plan complete)
#   active-plan-marker.sh get                    # Get current active plan
#   active-plan-marker.sh validate               # Validate marker is still valid
#
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="${SCRIPT_DIR}/active-plan-lib.sh"
[[ -r "$LIB" && ! -L "$LIB" ]] || exit 1
# shellcheck disable=SC1090,SC1091
source "$LIB"

COMMAND="${1:-}"
ARG="${2:-}"

case "$COMMAND" in
  set)
    if [[ -z "$ARG" ]]; then
      echo "Error: Plan directory required" >&2
      echo "Usage: $0 set <plan-directory>" >&2
      exit 1
    fi

    if ! is_valid_plan_dir "$ARG"; then
      echo "Error: Invalid plan directory: $ARG" >&2
      exit 1
    fi

    set_active_plan "$ARG"
    echo "Active plan set to: $(get_active_plan)"
    ;;
    
  clear)
    clear_active_plan
    echo "Active plan marker cleared"
    ;;
    
  get)
    ACTIVE=$(get_active_plan || true)
    if [[ -n "$ACTIVE" ]]; then
      echo "$ACTIVE"
    else
      echo "No active plan" >&2
      exit 1
    fi
    ;;
    
  validate)
    ACTIVE=$(get_active_plan || true)
    if [[ -n "$ACTIVE" ]]; then
      echo "Active plan: $ACTIVE"
      exit 0
    else
      echo "No valid active plan (marker cleared or stale)" >&2
      exit 1
    fi
    ;;
    
  *)
    echo "Active Plan Marker Management"
    echo ""
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "Commands:"
    echo "  set <dir>     Set active plan to directory"
    echo "  clear         Clear active plan marker (plan complete)"
    echo "  get           Get current active plan path"
    echo "  validate      Check if active plan is valid"
    echo ""
    echo "Marker file: $ACTIVE_PLAN_MARKER"
    exit 1
    ;;
esac
