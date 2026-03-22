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
if REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null); then
  :
else
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi
PROJECT_GEMFILE="${REPO_ROOT}/Gemfile"
PROJECT_LOCKFILE="${REPO_ROOT}/Gemfile.lock"

FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[[ -n "$FILE_PATH" ]] || exit 0
if [[ "$FILE_PATH" != /* ]]; then
  FILE_PATH="${REPO_ROOT}/${FILE_PATH#./}"
fi
[[ -f "$FILE_PATH" ]] || exit 0
[[ ! -L "$FILE_PATH" ]] || exit 0

case "$FILE_PATH" in
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
