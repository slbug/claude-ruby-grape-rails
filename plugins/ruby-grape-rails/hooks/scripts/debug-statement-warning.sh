#!/usr/bin/env bash
set -o nounset
set -o pipefail

HOOK_NAME="${BASH_SOURCE[0]##*/}"

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: ${HOOK_NAME} cannot inspect the hook payload because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before continuing." >&2
  exit 2
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

emit_debug_block() {
  local reason="$1"
  local remediation="$2"

  echo "BLOCKED: ${HOOK_NAME} could not inspect the edited Ruby file because ${reason}." >&2
  echo "$remediation" >&2
}

if [[ -z "$INPUT" ]]; then
  case "${HOOK_INPUT_STATUS:-empty}" in
  truncated | invalid)
    emit_debug_block \
      "the hook payload was ${HOOK_INPUT_STATUS}" \
      "Fix the hook input before retrying the edit."
    exit 2
    ;;
  esac
fi

REPO_ROOT=$(resolve_workspace_root "$INPUT") || {
  emit_debug_block \
    "the workspace root could not be resolved" \
    "Fix the hook payload or workspace layout before retrying the edit."
  exit 2
}
[[ -n "$REPO_ROOT" ]] || {
  emit_debug_block \
    "the workspace root could not be resolved" \
    "Fix the hook payload or workspace layout before retrying the edit."
  exit 2
}

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || {
  emit_debug_block \
    "tool_input.file_path could not be parsed" \
    "Fix the hook payload before retrying the edit."
  exit 2
}
[[ -n "$FILE_PATH" ]] || {
  emit_debug_block \
    "tool_input.file_path was missing" \
    "Fix the hook payload before retrying the edit."
  exit 2
}
FILE_PATH=$(resolve_workspace_file_path "$REPO_ROOT" "$FILE_PATH") || {
  emit_debug_block \
    "the edited path could not be resolved inside the workspace" \
    "Fix the hook payload before retrying the edit."
  exit 2
}
[[ -f "$FILE_PATH" ]] || {
  emit_debug_block \
    "the edited file was not found" \
    "Retry once the file exists on disk again."
  exit 2
}
[[ ! -L "$FILE_PATH" ]] || {
  emit_debug_block \
    "the edited file was a symlink" \
    "Use a regular file path before retrying the edit."
  exit 2
}
is_path_within_root "$REPO_ROOT" "$FILE_PATH" || {
  emit_debug_block \
    "the edited path resolved outside the workspace" \
    "Fix the hook payload before retrying the edit."
  exit 2
}

BASE_NAME=$(path_basename "$FILE_PATH")

case "$BASE_NAME" in
*.rb | *.rake | Gemfile | Rakefile | config.ru) ;;
*) exit 0 ;;
esac

[[ "$FILE_PATH" != */spec/* ]] || exit 0
[[ "$FILE_PATH" != */test/* ]] || exit 0
[[ "$FILE_PATH" != "${REPO_ROOT}/scripts/"* ]] || exit 0
[[ "$FILE_PATH" != "${REPO_ROOT}/plugins/ruby-grape-rails/scripts/"* ]] || exit 0

FILE_NAME="$BASE_NAME"
DEBUGS=""

# Grep original file for matches, then filter out comment-only lines from output
# to preserve original line numbers
for pattern in \
  'binding\.pry' \
  'binding\.irb' \
  '(^|[^[:alnum:]_])byebug([^[:alnum:]_]|$)' \
  '(^|[^[:alnum:]_])debugger([^[:alnum:]_]|$)' \
  '(^|[^[:alnum:]_.#])puts([[:space:]]|\(|$)' \
  '(^|[^[:alnum:]_.#])pp([[:space:]]|\(|$)' \
  '(^|[^[:alnum:]_.#])p([[:space:]]|\(|$)'; do
  MATCH=$(grep -nEm 3 "$pattern" -- "$FILE_PATH" 2>/dev/null | grep -v '^[0-9]*:[[:space:]]*#')
  [[ -n "$MATCH" ]] && DEBUGS+="
$MATCH"
done

if [[ -n "$DEBUGS" ]]; then
  cat >&2 <<MSG
DEBUG STATEMENTS in ${FILE_NAME}:
$(printf '%b' "$DEBUGS")

Remove before committing unless they are intentional operational logging.
MSG
  exit 2
fi
