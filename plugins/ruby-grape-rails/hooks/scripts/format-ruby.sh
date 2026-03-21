#!/usr/bin/env bash
# Auto-format Ruby files after write
# This hook runs automatically on PostToolUse for Edit/Write operations
#
# Hook input: JSON via stdin with .tool_input.file_path
# Auto-fixes formatting issues when possible

FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty')
[[ -n "$FILE_PATH" ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

case "$FILE_PATH" in
  *.rb|*.rake|Gemfile|Rakefile|config.ru) ;;
  *) exit 0 ;;
esac

has_gem() {
  local gem_name="$1"
  if [[ -f Gemfile.lock ]] && grep -Eq "^[[:space:]]{4}${gem_name} " Gemfile.lock; then
    return 0
  fi
  [[ -f Gemfile ]] && grep -Eq "gem ['\"]${gem_name}['\"]" Gemfile
}

if has_gem standard; then
  # Auto-fix with StandardRB
  if ! bundle exec standardrb "$FILE_PATH" --fix 2>/dev/null; then
    # If auto-fix failed, report for manual fixing
    echo "NEEDS FORMAT: $FILE_PATH — run 'bundle exec standardrb --fix $FILE_PATH'" >&2
    exit 2
  fi
elif has_gem rubocop; then
  # Auto-fix with RuboCop
  if ! bundle exec rubocop --force-exclusion "$FILE_PATH" -a 2>/dev/null; then
    # If auto-fix failed, report for manual fixing
    echo "NEEDS FORMAT OR LINT FIX: $FILE_PATH — run 'bundle exec rubocop -A $FILE_PATH'" >&2
    exit 2
  fi
fi
