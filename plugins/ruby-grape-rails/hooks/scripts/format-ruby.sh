#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Auto-format Ruby files after write
# This hook runs automatically on PostToolUse for Edit/Write operations
#
# Hook input: JSON via stdin with .tool_input.file_path
# Auto-fixes formatting issues when possible

HOOK_NAME="${BASH_SOURCE[0]##*/}"

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: ${HOOK_NAME} cannot inspect the hook payload because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before continuing." >&2
  exit 2
}

command -v jq >/dev/null 2>&1 || emit_missing_dependency_block "jq"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
DEP_LIB="${SCRIPT_DIR}/ruby-dependency-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
[[ -r "$DEP_LIB" && ! -L "$DEP_LIB" ]] || emit_missing_dependency_block "ruby-dependency-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
# shellcheck disable=SC1090,SC1091
source "$DEP_LIB"
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
if [[ -z "$INPUT" ]]; then
  case "${HOOK_INPUT_STATUS:-empty}" in
    truncated|invalid)
      echo "BLOCKED: ${HOOK_NAME} could not safely inspect a ${HOOK_INPUT_STATUS} hook payload." >&2
      echo "Fix the hook input before retrying automatic Ruby formatting." >&2
      exit 2
      ;;
  esac
fi
REPO_ROOT=$(resolve_workspace_root "$INPUT") || exit 0
[[ -n "$REPO_ROOT" ]] || exit 0
PROJECT_GEMFILE="${REPO_ROOT}/Gemfile"
PROJECT_LOCKFILE="${REPO_ROOT}/Gemfile.lock"

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

has_gem() {
  local gem_name="$1"
  ruby_plugin_repo_declares_gem "$REPO_ROOT" "$PROJECT_GEMFILE" "$gem_name" ||
    ruby_plugin_lock_has_gem "$PROJECT_LOCKFILE" "$gem_name"
}

printf -v QUOTED_PATH '%q' "$FILE_PATH"

report_formatter_failure() {
  local label="$1"
  local command_hint="$2"
  local err_file="$3"
  local err_preview=""

  if [[ -f "$err_file" && ! -L "$err_file" ]]; then
    err_preview=$(sed -n '1,5p' "$err_file" 2>/dev/null || true)
  fi

  echo "${label}: $FILE_PATH — run ${command_hint}" >&2
  if [[ -n "$err_preview" ]]; then
    printf 'Formatter output:\n%s\n' "$err_preview" >&2
  fi
}

emit_tempfile_failure_warning() {
  echo "BLOCKED: ${HOOK_NAME} could not run automatic Ruby formatting for ${FILE_PATH} because a temporary file could not be created." >&2
  echo "Fix TMPDIR permissions or disk space to restore automatic Ruby formatting." >&2
}

if has_gem standard; then
  if ! command -v bundle >/dev/null 2>&1; then
    echo "BLOCKED: ${HOOK_NAME} could not run automatic Ruby formatting for ${FILE_PATH} because Bundler is not available." >&2
    echo "Install Bundler to restore automatic StandardRB formatting." >&2
    exit 2
  fi
  # Auto-fix with StandardRB
  ERR_FILE=$(mktemp "${TMPDIR:-/tmp}/ruby-format.XXXXXX") || {
    emit_tempfile_failure_warning
    exit 2
  }
  if ! (cd "$REPO_ROOT" && bundle exec standardrb --fix -- "$FILE_PATH") 2>"$ERR_FILE"; then
    # If auto-fix failed, report for manual fixing
    report_formatter_failure "NEEDS FORMAT" "bundle exec standardrb --fix $QUOTED_PATH" "$ERR_FILE"
    safe_remove_temp_file "${ERR_FILE:-}" "${TMPDIR:-/tmp}/ruby-format.*" || true
    exit 2
  fi
  safe_remove_temp_file "${ERR_FILE:-}" "${TMPDIR:-/tmp}/ruby-format.*" || true
elif has_gem rubocop; then
  if ! command -v bundle >/dev/null 2>&1; then
    echo "BLOCKED: ${HOOK_NAME} could not run automatic Ruby formatting for ${FILE_PATH} because Bundler is not available." >&2
    echo "Install Bundler to restore automatic RuboCop formatting." >&2
    exit 2
  fi
  # Auto-fix with RuboCop
  ERR_FILE=$(mktemp "${TMPDIR:-/tmp}/ruby-format.XXXXXX") || {
    emit_tempfile_failure_warning
    exit 2
  }
  if ! (cd "$REPO_ROOT" && bundle exec rubocop --force-exclusion -a -- "$FILE_PATH") 2>"$ERR_FILE"; then
    # If auto-fix failed, report for manual fixing
    report_formatter_failure "NEEDS FORMAT OR LINT FIX" "bundle exec rubocop --force-exclusion -a $QUOTED_PATH" "$ERR_FILE"
    safe_remove_temp_file "${ERR_FILE:-}" "${TMPDIR:-/tmp}/ruby-format.*" || true
    exit 2
  fi
  safe_remove_temp_file "${ERR_FILE:-}" "${TMPDIR:-/tmp}/ruby-format.*" || true
fi
