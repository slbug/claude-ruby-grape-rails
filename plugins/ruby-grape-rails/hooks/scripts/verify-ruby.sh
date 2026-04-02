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

emit_verify_skip_warning() {
  local reason="$1"

  echo "WARNING: ${HOOK_NAME} skipped automatic Ruby verification because ${reason}." >&2
}

command -v jq >/dev/null 2>&1 || emit_missing_dependency_block "jq"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
if [[ -z "$INPUT" ]]; then
  case "${HOOK_INPUT_STATUS:-empty}" in
    truncated|invalid)
      echo "BLOCKED: ${HOOK_NAME} could not safely inspect a ${HOOK_INPUT_STATUS} hook payload." >&2
      echo "Fix the hook input before retrying automatic Ruby verification." >&2
      exit 2
      ;;
  esac
fi
REPO_ROOT=$(resolve_workspace_root "$INPUT") || {
  emit_verify_skip_warning "the workspace root could not be resolved"
  exit 0
}
if [[ -z "$REPO_ROOT" ]]; then
  emit_verify_skip_warning "the workspace root could not be resolved"
  exit 0
fi

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || {
  emit_verify_skip_warning "tool_input.file_path could not be parsed"
  exit 0
}
if [[ -z "$FILE_PATH" ]]; then
  emit_verify_skip_warning "tool_input.file_path was missing"
  exit 0
fi
FILE_PATH=$(resolve_workspace_file_path "$REPO_ROOT" "$FILE_PATH") || {
  emit_verify_skip_warning "the edited path could not be resolved inside the workspace"
  exit 0
}
[[ -f "$FILE_PATH" ]] || {
  emit_verify_skip_warning "the edited file was not found"
  exit 0
}
[[ ! -L "$FILE_PATH" ]] || {
  emit_verify_skip_warning "the edited file was a symlink"
  exit 0
}
is_path_within_root "$REPO_ROOT" "$FILE_PATH" || {
  emit_verify_skip_warning "the edited path resolved outside the workspace"
  exit 0
}

BASE_NAME=$(path_basename "$FILE_PATH")

emit_tempfile_failure_warning() {
  echo "⚠️  Ruby syntax verification skipped for ${FILE_PATH} because a temporary file could not be created." >&2
  echo "Fix TMPDIR permissions or disk space to restore automatic Ruby verification." >&2
}

case "$BASE_NAME" in
  *.rb|*.rake|Gemfile|Rakefile|config.ru)
    if ! command -v ruby >/dev/null 2>&1; then
      echo "⚠️  Ruby syntax check skipped for ${FILE_PATH} because ruby is not available." >&2
      echo "Install Ruby to restore automatic syntax verification." >&2
      exit 2
    fi
    TMP_OUTPUT=$(mktemp "${TMPDIR:-/tmp}/rb-verify.XXXXXX") || {
      emit_tempfile_failure_warning
      exit 2
    }
    [[ -n "$TMP_OUTPUT" ]] || {
      emit_tempfile_failure_warning
      exit 2
    }
    [[ "$TMP_OUTPUT" == "${TMPDIR:-/tmp}/rb-verify."* ]] || {
      emit_tempfile_failure_warning
      exit 2
    }

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
