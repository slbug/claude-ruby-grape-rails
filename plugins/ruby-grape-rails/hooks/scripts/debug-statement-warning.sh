#!/usr/bin/env bash
set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0
command -v grep >/dev/null 2>&1 || exit 0

FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[[ -n "$FILE_PATH" ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0
[[ ! -L "$FILE_PATH" ]] || exit 0

case "$FILE_PATH" in
  *.rb|*.rake|Gemfile|Rakefile) ;;
  *) exit 0 ;;
esac

[[ "$FILE_PATH" != */spec/* ]] || exit 0
[[ "$FILE_PATH" != */test/* ]] || exit 0

FILE_NAME="${FILE_PATH##*/}"
DEBUGS=""
for pattern in 'binding\.pry' 'binding\.irb' '\<byebug\>' '\<debugger\>' '^[[:space:]]*puts\>' '^[[:space:]]*pp\>'; do
  MATCH=$(grep -nEm 3 "$pattern" -- "$FILE_PATH" 2>/dev/null)
  [[ -n "$MATCH" ]] && DEBUGS+="
$MATCH"
done

if [[ -n "$DEBUGS" ]]; then
  cat >&2 <<MSG
DEBUG STATEMENTS in ${FILE_NAME}:
$(printf '%b' "$DEBUGS")

Remove before committing unless they are intentional operational logging.
MSG
  exit 2
fi
