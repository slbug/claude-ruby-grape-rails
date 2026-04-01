#!/usr/bin/env bash
set -o nounset
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
case "${HOOK_INPUT_STATUS:-empty}" in
  truncated|invalid)
    if [[ "${HOOK_INPUT_STATUS}" == "invalid" ]]; then
      echo "BLOCKED: rubyish-post-edit.sh could not safely inspect an invalid hook payload." >&2
    else
      echo "BLOCKED: rubyish-post-edit.sh could not safely inspect a truncated hook payload." >&2
    fi
    echo "Fix the hook input before retrying delegated Ruby post-edit hooks." >&2
    exit 2
    ;;
esac
STATUS=0

run_hook() {
  local target="$1"
  local code=0

  [[ -f "$target" && ! -L "$target" ]] || return 0

  printf '%s' "$INPUT" | "$target"
  code=$?
  if [[ "$code" -ne 0 ]]; then
    STATUS=$code
    return "$code"
  fi
}

run_hook "${SCRIPT_DIR}/iron-law-verifier.sh" || exit "$STATUS"
run_hook "${SCRIPT_DIR}/format-ruby.sh" || exit "$STATUS"
run_hook "${SCRIPT_DIR}/verify-ruby.sh" || exit "$STATUS"
run_hook "${SCRIPT_DIR}/debug-statement-warning.sh" || exit "$STATUS"

exit "$STATUS"
