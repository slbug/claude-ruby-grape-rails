#!/usr/bin/env bash
set -o nounset
set -o pipefail

command -v jq >/dev/null 2>&1 || exit 0
command -v ruby >/dev/null 2>&1 || exit 0

FILE_PATH=$(jq -r '.tool_input.file_path // empty' 2>/dev/null) || exit 0
[[ -n "$FILE_PATH" ]] || exit 0
[[ -f "$FILE_PATH" ]] || exit 0
[[ ! -L "$FILE_PATH" ]] || exit 0

case "$FILE_PATH" in
  *.rb|*.rake|Gemfile|Rakefile|config.ru)
    TMP_OUTPUT=$(mktemp "${TMPDIR:-/tmp}/rb-verify.XXXXXX") || exit 0
    [[ -n "$TMP_OUTPUT" ]] || exit 0

    cleanup() {
      rm -f -- "$TMP_OUTPUT"
    }
    trap cleanup EXIT HUP INT TERM

    ruby -c -- "$FILE_PATH" >"$TMP_OUTPUT" 2>&1 || {
      cat -- "$TMP_OUTPUT" >&2
      exit 2
    }
    ;;
  *)
    exit 0
    ;;
esac
