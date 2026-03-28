#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Auto-format Ruby files after write
# This hook runs automatically on PostToolUse for Edit/Write operations
#
# Hook input: JSON via stdin with .tool_input.file_path
# Auto-fixes formatting issues when possible

command -v jq >/dev/null 2>&1 || exit 0
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
INPUT=$(read_hook_input)
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
  if [[ -f "$PROJECT_LOCKFILE" ]] && grep -Fq "    ${gem_name} " "$PROJECT_LOCKFILE"; then
    return 0
  fi
  [[ -f "$PROJECT_GEMFILE" ]] && (
    grep -Fq "gem \"${gem_name}\"" "$PROJECT_GEMFILE" ||
      grep -Fq "gem '${gem_name}'" "$PROJECT_GEMFILE"
  )
}

command -v bundle >/dev/null 2>&1 || exit 0
printf -v QUOTED_PATH '%q' "$FILE_PATH"

report_formatter_failure() {
  local label="$1"
  local command_hint="$2"
  local err_file="$3"
  local err_preview=""

  if [[ -f "$err_file" && ! -L "$err_file" ]]; then
    err_preview=$(sed -n '1,5p' "$err_file" 2>/dev/null || true)
  fi

  echo "${label}: $FILE_PATH — run '${command_hint}'" >&2
  if [[ -n "$err_preview" ]]; then
    printf 'Formatter output:\n%s\n' "$err_preview" >&2
  fi
}

if has_gem standard; then
  # Auto-fix with StandardRB
  ERR_FILE=$(mktemp "${TMPDIR:-/tmp}/ruby-format.XXXXXX") || exit 0
  if ! (cd "$REPO_ROOT" && bundle exec standardrb --fix -- "$FILE_PATH") 2>"$ERR_FILE"; then
    # If auto-fix failed, report for manual fixing
    report_formatter_failure "NEEDS FORMAT" "bundle exec standardrb --fix $QUOTED_PATH" "$ERR_FILE"
    rm -f -- "$ERR_FILE"
    exit 2
  fi
  rm -f -- "$ERR_FILE"
elif has_gem rubocop; then
  # Auto-fix with RuboCop
  ERR_FILE=$(mktemp "${TMPDIR:-/tmp}/ruby-format.XXXXXX") || exit 0
  if ! (cd "$REPO_ROOT" && bundle exec rubocop --force-exclusion -a -- "$FILE_PATH") 2>"$ERR_FILE"; then
    # If auto-fix failed, report for manual fixing
    report_formatter_failure "NEEDS FORMAT OR LINT FIX" "bundle exec rubocop --force-exclusion -a $QUOTED_PATH" "$ERR_FILE"
    rm -f -- "$ERR_FILE"
    exit 2
  fi
  rm -f -- "$ERR_FILE"
fi
