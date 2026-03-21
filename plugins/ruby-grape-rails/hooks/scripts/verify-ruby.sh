#!/usr/bin/env bash

FILE_PATH=$(cat | jq -r '.tool_input.file_path // empty')
[[ -n "$FILE_PATH" ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0

case "$FILE_PATH" in
  *.rb|*.rake|Gemfile|Rakefile|config.ru)
    ruby -c "$FILE_PATH" >/tmp/rb-verify.out 2>&1 || {
      cat /tmp/rb-verify.out >&2
      exit 2
    }
    ;;
  *)
    exit 0
    ;;
esac
