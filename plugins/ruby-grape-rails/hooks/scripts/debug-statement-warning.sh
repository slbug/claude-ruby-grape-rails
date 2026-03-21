#!/usr/bin/env bash

FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty')
[[ -n "$FILE_PATH" ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

case "$FILE_PATH" in
  *.rb|*.rake|Gemfile|Rakefile) ;;
  *) exit 0 ;;
esac

[[ "$FILE_PATH" != */spec/* ]] || exit 0
[[ "$FILE_PATH" != */test/* ]] || exit 0

DEBUGS=""
for pattern in 'binding\.pry' 'binding\.irb' '\<byebug\>' '\<debugger\>' '^[[:space:]]*puts\>' '^[[:space:]]*pp\>'; do
  MATCH=$(grep -nE "$pattern" "$FILE_PATH" 2>/dev/null | head -3)
  [[ -n "$MATCH" ]] && DEBUGS+="
$MATCH"
done

if [[ -n "$DEBUGS" ]]; then
  cat >&2 <<MSG
DEBUG STATEMENTS in $(basename "$FILE_PATH"):
$(echo -e "$DEBUGS")

Remove before committing unless they are intentional operational logging.
MSG
  exit 2
fi
