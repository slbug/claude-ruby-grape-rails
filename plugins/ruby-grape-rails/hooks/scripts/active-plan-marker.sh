#!/usr/bin/env bash
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

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/active-plan-lib.sh"

COMMAND="${1:-}"
ARG="${2:-}"

case "$COMMAND" in
  set)
    if [[ -z "$ARG" ]]; then
      echo "Error: Plan directory required" >&2
      echo "Usage: $0 set <plan-directory>" >&2
      exit 1
    fi
    
    if [[ ! -d "$ARG" ]]; then
      echo "Error: Not a directory: $ARG" >&2
      exit 1
    fi
    
    set_active_plan "$ARG"
    echo "Active plan set to: $ARG"
    ;;
    
  clear)
    clear_active_plan
    echo "Active plan marker cleared"
    ;;
    
  get)
    ACTIVE=$(get_active_plan)
    if [[ -n "$ACTIVE" ]]; then
      echo "$ACTIVE"
    else
      echo "No active plan" >&2
      exit 1
    fi
    ;;
    
  validate)
    ACTIVE=$(get_active_plan)
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
