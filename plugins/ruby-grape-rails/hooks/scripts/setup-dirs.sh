#!/usr/bin/env bash
set -o nounset
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi

# SessionStart hook: Create core workflow directories (other dirs created by skills on demand)
if ! mkdir -p -- \
  "${REPO_ROOT}/.claude/plans" \
  "${REPO_ROOT}/.claude/reviews" \
  "${REPO_ROOT}/.claude/solutions" \
  "${REPO_ROOT}/.claude/audit" \
  "${REPO_ROOT}/.claude/skill-metrics" 2>/dev/null; then
  echo "Warning: could not create one or more .claude workflow directories" >&2
fi
