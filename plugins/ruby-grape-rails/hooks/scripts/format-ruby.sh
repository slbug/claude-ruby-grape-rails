#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Auto-format Ruby files after write
# This hook runs automatically on PostToolUse for Edit/Write operations
#
# Hook input: JSON via stdin with .tool_input.file_path
# Auto-fixes formatting issues when possible

command -v jq >/dev/null 2>&1 || exit 0
INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
REPO_ROOT=$(resolve_workspace_root "$INPUT")
PROJECT_GEMFILE="${REPO_ROOT}/Gemfile"
PROJECT_LOCKFILE="${REPO_ROOT}/Gemfile.lock"

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[[ -n "$FILE_PATH" ]] || exit 0
FILE_PATH=$(resolve_workspace_file_path "$REPO_ROOT" "$FILE_PATH") || exit 0
[[ -f "$FILE_PATH" ]] || exit 0
[[ ! -L "$FILE_PATH" ]] || exit 0
is_path_within_root "$REPO_ROOT" "$FILE_PATH" || exit 0

BASE_NAME=$(basename -- "$FILE_PATH")
case "$BASE_NAME" in
  *.rb|*.rake|Gemfile|Rakefile|config.ru) ;;
  *) exit 0 ;;
esac

has_gem() {
  local gem_name="$1"
  if [[ -f "$PROJECT_LOCKFILE" ]] && grep -Eq "^[[:space:]]{4}${gem_name} " "$PROJECT_LOCKFILE"; then
    return 0
  fi
  [[ -f "$PROJECT_GEMFILE" ]] && grep -Eq "gem ['\"]${gem_name}['\"]" "$PROJECT_GEMFILE"
}

command -v bundle >/dev/null 2>&1 || exit 0
printf -v QUOTED_PATH '%q' "$FILE_PATH"

if has_gem standard; then
  # Auto-fix with StandardRB
  if ! (cd "$REPO_ROOT" && bundle exec standardrb --fix -- "$FILE_PATH") 2>/dev/null; then
    # If auto-fix failed, report for manual fixing
    echo "NEEDS FORMAT: $FILE_PATH — run 'bundle exec standardrb --fix $QUOTED_PATH'" >&2
    exit 2
  fi
elif has_gem rubocop; then
  # Auto-fix with RuboCop
  if ! (cd "$REPO_ROOT" && bundle exec rubocop --force-exclusion -a -- "$FILE_PATH") 2>/dev/null; then
    # If auto-fix failed, report for manual fixing
    echo "NEEDS FORMAT OR LINT FIX: $FILE_PATH — run 'bundle exec rubocop -A $QUOTED_PATH'" >&2
    exit 2
  fi
fi
