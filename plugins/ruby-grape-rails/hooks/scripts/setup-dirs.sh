#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: advisory — warn/skip on degraded state, exit 0.


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
case "${HOOK_INPUT_STATUS:-empty}" in
  truncated|invalid)
    echo "Warning: skipping setup-dirs.sh because hook input was ${HOOK_INPUT_STATUS}" >&2
    append_hook_degradation_log "setup-dirs.sh" "session directory bootstrap skipped because hook input was ${HOOK_INPUT_STATUS}" "$INPUT" || true
    exit 0
    ;;
esac
REPO_ROOT=$(resolve_workspace_root "$INPUT") || {
  append_hook_degradation_log "setup-dirs.sh" "session directory bootstrap skipped because workspace root could not be resolved" "$INPUT" || true
  exit 0
}
if [[ -z "$REPO_ROOT" ]]; then
  append_hook_degradation_log "setup-dirs.sh" "session directory bootstrap skipped because workspace root could not be resolved" "$INPUT" || true
  exit 0
fi
CLAUDE_DIR="${REPO_ROOT}/.claude"

[[ ! -L "$CLAUDE_DIR" ]] || exit 0

# SessionStart hook: Create core workflow directories (other dirs created by skills on demand)
if ! mkdir -p -- \
  "${CLAUDE_DIR}/plans" \
  "${CLAUDE_DIR}/research" \
  "${CLAUDE_DIR}/reviews" \
  "${CLAUDE_DIR}/solutions" \
  "${CLAUDE_DIR}/audit" \
  "${CLAUDE_DIR}/skill-metrics" 2>/dev/null; then
  echo "Warning: could not create one or more .claude workflow directories" >&2
fi
