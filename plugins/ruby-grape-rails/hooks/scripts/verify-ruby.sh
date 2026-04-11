#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: delegated Ruby post-edit guardrail; once selected for a Ruby-ish path,
# payload and path-resolution failures block rather than silently skipping.

HOOK_NAME="${BASH_SOURCE[0]##*/}"

RUBY_PLUGIN_RUBY_CHECK_TIMEOUT="${RUBY_PLUGIN_RUBY_CHECK_TIMEOUT:-30}"

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: ${HOOK_NAME} cannot inspect the hook payload because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before continuing." >&2
  exit 2
}

emit_verify_block() {
  local reason="$1"
  local remediation="$2"

  echo "BLOCKED: ${HOOK_NAME} could not run automatic Ruby verification because ${reason}." >&2
  echo "$remediation" >&2
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
  emit_verify_block \
    "the workspace root could not be resolved" \
    "Fix the hook payload or workspace layout before retrying automatic Ruby verification."
  exit 2
}
if [[ -z "$REPO_ROOT" ]]; then
  emit_verify_block \
    "the workspace root could not be resolved" \
    "Fix the hook payload or workspace layout before retrying automatic Ruby verification."
  exit 2
fi

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || {
  emit_verify_block \
    "tool_input.file_path could not be parsed" \
    "Fix the hook payload before retrying automatic Ruby verification."
  exit 2
}
if [[ -z "$FILE_PATH" ]]; then
  emit_verify_block \
    "tool_input.file_path was missing" \
    "Fix the hook payload before retrying automatic Ruby verification."
  exit 2
fi
FILE_PATH=$(resolve_workspace_file_path "$REPO_ROOT" "$FILE_PATH") || {
  emit_verify_block \
    "the edited path could not be resolved inside the workspace" \
    "Fix the hook payload before retrying automatic Ruby verification."
  exit 2
}
[[ -f "$FILE_PATH" ]] || {
  emit_verify_block \
    "the edited file was not found" \
    "Retry once the file exists on disk again."
  exit 2
}
[[ ! -L "$FILE_PATH" ]] || {
  emit_verify_block \
    "the edited file was a symlink" \
    "Use a regular file path before retrying automatic Ruby verification."
  exit 2
}
is_path_within_root "$REPO_ROOT" "$FILE_PATH" || {
  emit_verify_block \
    "the edited path resolved outside the workspace" \
    "Fix the hook payload before retrying automatic Ruby verification."
  exit 2
}

BASE_NAME=$(path_basename "$FILE_PATH")

emit_tempfile_failure_warning() {
  emit_verify_block \
    "a temporary file could not be created for ${FILE_PATH}" \
    "Fix TMPDIR permissions or disk space to restore automatic Ruby verification."
}

case "$BASE_NAME" in
  *.rb|*.rake|Gemfile|Rakefile|config.ru)
    if ! command -v ruby >/dev/null 2>&1; then
      emit_verify_block \
        "ruby is not available for ${FILE_PATH}" \
        "Install Ruby to restore automatic syntax verification."
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

    timeout "$RUBY_PLUGIN_RUBY_CHECK_TIMEOUT" ruby -c -- "$FILE_PATH" >"$TMP_OUTPUT" 2>&1
    VERIFY_STATUS=$?
    if [[ "$VERIFY_STATUS" -eq 124 ]]; then
      echo "WARNING: ruby -c timed out after ${RUBY_PLUGIN_RUBY_CHECK_TIMEOUT}s. Skipping syntax check." >&2
    elif [[ "$VERIFY_STATUS" -ne 0 ]]; then
      cat -- "$TMP_OUTPUT" >&2
      exit 2
    fi
    ;;
  *)
    exit 0
    ;;
esac
