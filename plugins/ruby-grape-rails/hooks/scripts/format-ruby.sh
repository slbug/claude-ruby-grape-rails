#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Auto-format Ruby files after write
# This hook runs automatically on PostToolUse for Edit/Write operations
#
# Hook input: JSON via stdin with .tool_input.file_path
# Auto-fixes formatting issues when possible
# Policy: delegated Ruby post-edit guardrail; once selected for a Ruby-ish path,
# payload and path-resolution failures block rather than silently skipping.

HOOK_NAME="${BASH_SOURCE[0]##*/}"

# Configurable timeout for formatter commands (seconds).
RUBY_PLUGIN_FORMATTER_TIMEOUT="${RUBY_PLUGIN_FORMATTER_TIMEOUT:-120}"

# Resolve timeout command (macOS ships without `timeout`; coreutils provides `gtimeout`).
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD="gtimeout"
else
  TIMEOUT_CMD=""
fi

# Run command with timeout if available, otherwise run directly.
run_with_timeout() {
  local secs="$1"; shift
  if [[ -n "$TIMEOUT_CMD" ]]; then
    "$TIMEOUT_CMD" "$secs" "$@"
  else
    "$@"
  fi
}

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

emit_format_block() {
  local reason="$1"
  local remediation="$2"

  echo "BLOCKED: ${HOOK_NAME} could not run automatic Ruby formatting because ${reason}." >&2
  echo "$remediation" >&2
}

if [[ -z "$INPUT" ]]; then
  case "${HOOK_INPUT_STATUS:-empty}" in
    truncated|invalid)
      echo "BLOCKED: ${HOOK_NAME} could not safely inspect a ${HOOK_INPUT_STATUS} hook payload." >&2
      echo "Fix the hook input before retrying automatic Ruby formatting." >&2
      exit 2
      ;;
  esac
fi
REPO_ROOT=$(resolve_workspace_root "$INPUT") || {
  emit_format_block \
    "the workspace root could not be resolved" \
    "Fix the hook payload or workspace layout before retrying automatic Ruby formatting."
  exit 2
}
[[ -n "$REPO_ROOT" ]] || {
  emit_format_block \
    "the workspace root could not be resolved" \
    "Fix the hook payload or workspace layout before retrying automatic Ruby formatting."
  exit 2
}
PROJECT_GEMFILE="${REPO_ROOT}/Gemfile"
PROJECT_LOCKFILE="${REPO_ROOT}/Gemfile.lock"

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || {
  emit_format_block \
    "tool_input.file_path could not be parsed" \
    "Fix the hook payload before retrying automatic Ruby formatting."
  exit 2
}
[[ -n "$FILE_PATH" ]] || {
  emit_format_block \
    "tool_input.file_path was missing" \
    "Fix the hook payload before retrying automatic Ruby formatting."
  exit 2
}
FILE_PATH=$(resolve_workspace_file_path "$REPO_ROOT" "$FILE_PATH") || {
  emit_format_block \
    "the edited path could not be resolved inside the workspace" \
    "Fix the hook payload before retrying automatic Ruby formatting."
  exit 2
}
[[ -f "$FILE_PATH" ]] || {
  emit_format_block \
    "the edited file was not found" \
    "Retry once the file exists on disk again."
  exit 2
}
[[ ! -L "$FILE_PATH" ]] || {
  emit_format_block \
    "the edited file was a symlink" \
    "Use a regular file path before retrying automatic Ruby formatting."
  exit 2
}
is_path_within_root "$REPO_ROOT" "$FILE_PATH" || {
  emit_format_block \
    "the edited path resolved outside the workspace" \
    "Fix the hook payload before retrying automatic Ruby formatting."
  exit 2
}

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

gem_declared_now() {
  local gem_name="$1"
  ruby_plugin_repo_declares_gem "$REPO_ROOT" "$PROJECT_GEMFILE" "$gem_name"
}

gem_locked_now() {
  local gem_name="$1"
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

emit_ambiguous_formatter_warning() {
  echo "WARNING: ${HOOK_NAME} skipped automatic Ruby formatting for ${FILE_PATH} because formatter dependencies are in transition between Gemfile and Gemfile.lock." >&2
  echo "Finish the formatter dependency change, refresh the lockfile, then rerun formatting explicitly." >&2
}

STANDARD_DECLARED=false
STANDARD_LOCKED=false
RUBOCOP_DECLARED=false
RUBOCOP_LOCKED=false

gem_declared_now standard && STANDARD_DECLARED=true
gem_locked_now standard && STANDARD_LOCKED=true
gem_declared_now rubocop && RUBOCOP_DECLARED=true
gem_locked_now rubocop && RUBOCOP_LOCKED=true

if [[ "$BASE_NAME" == "Gemfile" || "$BASE_NAME" == "Gemfile.lock" ]]; then
  if [[ "$STANDARD_DECLARED" != "$STANDARD_LOCKED" || "$RUBOCOP_DECLARED" != "$RUBOCOP_LOCKED" ]]; then
    emit_ambiguous_formatter_warning
    exit 0
  fi
fi

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
  (cd "$REPO_ROOT" && run_with_timeout "$RUBY_PLUGIN_FORMATTER_TIMEOUT" bundle exec standardrb --fix -- "$FILE_PATH") 2>"$ERR_FILE"
  FMT_STATUS=$?
  if [[ -n "$TIMEOUT_CMD" && "$FMT_STATUS" -eq 124 ]]; then
    echo "BLOCKED: standardrb timed out after ${RUBY_PLUGIN_FORMATTER_TIMEOUT}s." >&2
    echo "Raise timeout: export RUBY_PLUGIN_FORMATTER_TIMEOUT=300" >&2
    safe_remove_temp_file "${ERR_FILE:-}" "${TMPDIR:-/tmp}/ruby-format.*" || true
    exit 2
  elif [[ "$FMT_STATUS" -ne 0 ]]; then
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
  (cd "$REPO_ROOT" && run_with_timeout "$RUBY_PLUGIN_FORMATTER_TIMEOUT" bundle exec rubocop --force-exclusion -a -- "$FILE_PATH") 2>"$ERR_FILE"
  FMT_STATUS=$?
  if [[ -n "$TIMEOUT_CMD" && "$FMT_STATUS" -eq 124 ]]; then
    echo "BLOCKED: rubocop timed out after ${RUBY_PLUGIN_FORMATTER_TIMEOUT}s." >&2
    echo "Raise timeout: export RUBY_PLUGIN_FORMATTER_TIMEOUT=300" >&2
    safe_remove_temp_file "${ERR_FILE:-}" "${TMPDIR:-/tmp}/ruby-format.*" || true
    exit 2
  elif [[ "$FMT_STATUS" -ne 0 ]]; then
    # If auto-fix failed, report for manual fixing
    report_formatter_failure "NEEDS FORMAT OR LINT FIX" "bundle exec rubocop --force-exclusion -a $QUOTED_PATH" "$ERR_FILE"
    safe_remove_temp_file "${ERR_FILE:-}" "${TMPDIR:-/tmp}/ruby-format.*" || true
    exit 2
  fi
  safe_remove_temp_file "${ERR_FILE:-}" "${TMPDIR:-/tmp}/ruby-format.*" || true
fi
