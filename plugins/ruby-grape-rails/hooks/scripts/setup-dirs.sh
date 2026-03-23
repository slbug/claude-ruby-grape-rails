#!/usr/bin/env bash
set -o nounset
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
INPUT=$(read_hook_input)
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0
CLAUDE_DIR="${REPO_ROOT}/.claude"

[[ ! -L "$CLAUDE_DIR" ]] || exit 0

# SessionStart hook: Create core workflow directories (other dirs created by skills on demand)
if ! mkdir -p -- \
  "${CLAUDE_DIR}/plans" \
  "${CLAUDE_DIR}/reviews" \
  "${CLAUDE_DIR}/solutions" \
  "${CLAUDE_DIR}/audit" \
  "${CLAUDE_DIR}/skill-metrics" 2>/dev/null; then
  echo "Warning: could not create one or more .claude workflow directories" >&2
fi
