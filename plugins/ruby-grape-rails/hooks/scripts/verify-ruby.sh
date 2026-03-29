#!/usr/bin/env bash
set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0
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
  *.rb|*.rake|Gemfile|Rakefile|config.ru)
    if ! command -v ruby >/dev/null 2>&1; then
      echo "⚠️  Ruby syntax check skipped for ${FILE_PATH} because ruby is not available." >&2
      echo "Install Ruby to restore automatic syntax verification." >&2
      exit 2
    fi
    TMP_OUTPUT=$(mktemp "${TMPDIR:-/tmp}/rb-verify.XXXXXX") || exit 0
    [[ -n "$TMP_OUTPUT" ]] || exit 0
    [[ "$TMP_OUTPUT" == "${TMPDIR:-/tmp}/rb-verify."* ]] || exit 0

    cleanup() {
      safe_remove_temp_file "${TMP_OUTPUT:-}" "${TMPDIR:-/tmp}/rb-verify.*" || true
    }
    trap cleanup EXIT HUP INT TERM

    ruby -c -- "$FILE_PATH" >"$TMP_OUTPUT" 2>&1 || {
      cat -- "$TMP_OUTPUT" >&2
      exit 2
    }
    ;;
  *)
    exit 0
    ;;
esac
