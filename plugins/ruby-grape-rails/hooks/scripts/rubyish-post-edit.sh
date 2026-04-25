#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Delegated Ruby-ish post-edit entrypoint.
# Policy: delegated Ruby guardrail — fail closed on malformed payloads or
# missing delegates, but aggregate delegate diagnostics so one failure
# does not mask later high-signal warnings.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: rubyish-post-edit.sh cannot inspect Ruby edits because ${dependency} is unavailable." >&2
  echo "Restore the dependency or disable the delegated post-edit hook explicitly before continuing." >&2
  exit 2
}

[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
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
FAILURES=0

run_hook() {
  local target="$1"
  local code=0

  [[ -f "$target" && ! -L "$target" ]] || emit_missing_dependency_block "$(path_basename "$target")"

  printf '%s' "$INPUT" | "$target"
  code=$?
  if [[ "$code" -ne 0 ]]; then
    FAILURES=$((FAILURES + 1))
    if [[ "$code" -eq 2 ]]; then
      STATUS=2
    elif [[ "$STATUS" -eq 0 ]]; then
      STATUS=$code
    fi
  fi

  return 0
}

run_hook "${SCRIPT_DIR}/iron-law-verifier.sh"
run_hook "${SCRIPT_DIR}/format-ruby.sh"
run_hook "${SCRIPT_DIR}/verify-ruby.sh"
run_hook "${SCRIPT_DIR}/debug-statement-warning.sh"

if [[ "$FAILURES" -gt 1 ]]; then
  echo "BLOCKED: rubyish-post-edit.sh saw ${FAILURES} delegated post-edit failures; see diagnostics above." >&2
fi

exit "$STATUS"
