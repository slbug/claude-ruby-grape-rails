#!/usr/bin/env bash
set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0
command -v grep >/dev/null 2>&1 || exit 0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
INPUT=$(read_hook_input)
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[[ -n "$FILE_PATH" ]] || exit 0
FILE_PATH=$(resolve_workspace_file_path "$REPO_ROOT" "$FILE_PATH") || exit 0
[[ -f "$FILE_PATH" ]] || exit 0
[[ ! -L "$FILE_PATH" ]] || exit 0
is_path_within_root "$REPO_ROOT" "$FILE_PATH" || exit 0

BASE_NAME=$(path_basename "$FILE_PATH")

case "$BASE_NAME" in
  *.rb|*.rake|Gemfile|Rakefile|config.ru) ;;
  *) exit 0 ;;
esac

[[ "$FILE_PATH" != */spec/* ]] || exit 0
[[ "$FILE_PATH" != */test/* ]] || exit 0
[[ "$FILE_PATH" != "${REPO_ROOT}/scripts/"* ]] || exit 0
[[ "$FILE_PATH" != "${REPO_ROOT}/plugins/ruby-grape-rails/scripts/"* ]] || exit 0

FILE_NAME="$BASE_NAME"
DEBUGS=""
for pattern in 'binding\.pry' 'binding\.irb' '\<byebug\>' '\<debugger\>' '^[[:space:]]*puts\>' '^[[:space:]]*pp\>'; do
  MATCH=$(grep -nEm 3 "$pattern" -- "$FILE_PATH" 2>/dev/null)
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
