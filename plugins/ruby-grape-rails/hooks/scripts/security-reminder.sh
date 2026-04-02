#!/usr/bin/env bash
set -o nounset
set -o pipefail

HOOK_NAME="${BASH_SOURCE[0]##*/}"

emit_missing_dependency_block() {
  local dependency="$1"

  echo "WARNING: ${HOOK_NAME} cannot inspect the hook payload because ${dependency} is unavailable." >&2
  echo "Install the missing dependency to restore security-sensitive file reminders." >&2
  exit 0
}

emit_resolution_warning() {
  local reason="$1"

  echo "WARNING: ${HOOK_NAME} could not inspect the edited path because ${reason}." >&2
  echo "Fix the hook payload or workspace mapping to restore security-sensitive file reminders." >&2
  exit 0
}

command -v jq >/dev/null 2>&1 || emit_missing_dependency_block "jq"
command -v grep >/dev/null 2>&1 || emit_missing_dependency_block "grep"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
case "${HOOK_INPUT_STATUS:-empty}" in
  invalid)
    echo "WARNING: ${HOOK_NAME} could not inspect an invalid hook payload." >&2
    exit 0
    ;;
  truncated)
    echo "WARNING: ${HOOK_NAME} could not inspect a truncated hook payload." >&2
    exit 0
    ;;
esac
REPO_ROOT=$(resolve_workspace_root "$INPUT") || {
  emit_resolution_warning "the workspace root could not be resolved"
}
if [[ -z "$REPO_ROOT" ]]; then
  emit_resolution_warning "the workspace root could not be resolved"
fi

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || {
  emit_resolution_warning "tool_input.file_path could not be parsed"
}
if [[ -z "$FILE_PATH" ]]; then
  emit_resolution_warning "tool_input.file_path was missing"
fi
FILE_PATH=$(resolve_workspace_file_path "$REPO_ROOT" "$FILE_PATH") || {
  emit_resolution_warning "the edited path could not be resolved inside the workspace"
}
is_path_within_root "$REPO_ROOT" "$FILE_PATH" || {
  emit_resolution_warning "the edited path resolved outside the workspace"
}

FILE_NAME=$(path_basename "$FILE_PATH")
LOWER_PATH=$(printf '%s' "$FILE_PATH" | tr '[:upper:]' '[:lower:]')
if printf '%s' "$LOWER_PATH" | grep -qiE '(^|/|[._-])(auth|authentication|session|sessions|password|passwords|token|tokens|login|credential|credentials|secret|secrets|oauth|policy|policies|ability|abilities|admin|payment|payments|permission|permissions)(/|[._-]|$)'; then
  cat >&2 <<MSG
WARNING: security-sensitive file detected: ${FILE_NAME}
Check these before moving on:
- authorization/policy coverage
- explicit params shaping (strong params or Grape declared params)
- no SQL interpolation
- no html_safe/raw on untrusted content
- Sidekiq enqueue-after-commit discipline for security-sensitive writes
Consider: /rb:review security
MSG
  exit 0
fi
