#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Check if current branch is behind origin/main and warn if so.
#
# NOTE: This script is a UTILITY script, not currently auto-wired in hooks.json.
# It can be run manually or re-added to SessionStart if branch freshness checks
# are desired. To use: run this script directly or add to hooks.json SessionStart.
#
# Silent when branch is up to date or on main/master.

# Only run in git repos
git rev-parse --is-inside-work-tree &>/dev/null || exit 0

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
case "$BRANCH" in
  main|master|HEAD) exit 0 ;;
esac

# Fetch quietly (ignore failures — offline is fine)
git fetch --quiet 2>/dev/null

# Count commits behind main (try main, then master)
BASE="origin/main"
git rev-parse --verify "$BASE" &>/dev/null || BASE="origin/master"
git rev-parse --verify "$BASE" &>/dev/null || exit 0

BEHIND=$(git rev-list --count HEAD.."$BASE" 2>/dev/null)
[[ -n "$BEHIND" && "$BEHIND" -gt 0 ]] || exit 0

echo "⚠ Branch '$BRANCH' is $BEHIND commits behind main. Consider rebasing."
