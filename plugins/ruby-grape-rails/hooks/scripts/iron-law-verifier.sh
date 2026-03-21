#!/usr/bin/env bash

FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty')
[[ -n "$FILE_PATH" ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

case "$FILE_PATH" in
  *.rb|*.rake|Gemfile|Rakefile|config.ru) ;;
  *) exit 0 ;;
esac

VIOLATIONS=""

check_violation() {
  local pattern="$1"
  grep -En "$pattern" "$FILE_PATH" 2>/dev/null | while IFS= read -r line; do
    content="${line#*:}"
    trimmed="${content#"${content%%[! ]*}"}"
    if [[ "$trimmed" != \#* ]]; then
      echo "$line"
      break
    fi
  done
}

MATCH=$(check_violation '(t|add_column)\.float[[:space:]]+:(price|amount|cost|total|balance|fee|rate|charge|payment|salary|wage|budget|revenue|discount)')
if [[ -n "$MATCH" ]]; then
  LINE=$(echo "$MATCH" | cut -d: -f1)
  VIOLATIONS+="
- Iron Law (line $LINE): float used for money-like column — use decimal or integer cents"
fi

MATCH=$(check_violation 'where\(".*#\{|order\(".*#\{|find_by_sql\(".*#\{')
if [[ -n "$MATCH" ]]; then
  LINE=$(echo "$MATCH" | cut -d: -f1)
  VIOLATIONS+="
- Iron Law (line $LINE): SQL interpolation detected — use bind params, hashes, Arel, or sanitized fragments"
fi

MATCH=$(check_violation '(^|[^.])(raw\(|\.html_safe([[:space:]]|\(|$))')
if [[ -n "$MATCH" ]]; then
  LINE=$(echo "$MATCH" | cut -d: -f1)
  VIOLATIONS+="
- Iron Law (line $LINE): unsafe HTML rendering detected — sanitize or render escaped content"
fi

MATCH=$(check_violation 'update_columns\(|update_column\(|save\(validate:[[:space:]]*false\)')
if [[ -n "$MATCH" ]]; then
  LINE=$(echo "$MATCH" | cut -d: -f1)
  VIOLATIONS+="
- Iron Law (line $LINE): validation/callback bypass detected — justify explicitly or use normal persistence paths"
fi

MATCH=$(check_violation 'default_scope([[:space:]]|$)')
if [[ -n "$MATCH" ]]; then
  LINE=$(echo "$MATCH" | cut -d: -f1)
  VIOLATIONS+="
- Iron Law (line $LINE): default_scope detected — prefer explicit named scopes"
fi

MATCH=$(check_violation 'perform_async\([^)]*(current_|@|params\[|\w+\.attributes|\w+\.as_json)')
if [[ -n "$MATCH" ]]; then
  LINE=$(echo "$MATCH" | cut -d: -f1)
  VIOLATIONS+="
- Iron Law (line $LINE): suspicious Sidekiq payload detected — pass IDs and simple JSON-safe primitives only"
fi

if [[ -n "$VIOLATIONS" ]]; then
  cat >&2 <<MSG
RUBY IRON LAW VIOLATION(S) in $(basename "$FILE_PATH"):
$(echo -e "$VIOLATIONS")

Fix these before proceeding.
MSG
  exit 2
fi
