#!/usr/bin/env bash
set -o nounset
set -o pipefail

HOOK_NAME="${BASH_SOURCE[0]##*/}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INPUT=$(cat)
LAST_HOOK_OUTPUT=""

emit_missing_hook_block() {
  local target_name="$1"

  echo "BLOCKED: ${HOOK_NAME} could not run ${target_name} because the hook script is unavailable." >&2
  echo "Restore the missing hook script before retrying the failed Ruby command." >&2
  exit 2
}

run_hook() {
  local target="$1"
  local target_name="${target##*/}"
  local output=""
  local code=0
  local stdout_file=""
  local stderr_file=""

  if [[ ! -f "$target" || -L "$target" ]]; then
    emit_missing_hook_block "$target_name"
  fi

  stdout_file=$(mktemp "${TMPDIR:-/tmp}/${HOOK_NAME}.${target_name}.stdout.XXXXXX") || {
    echo "BLOCKED: ${HOOK_NAME} could not capture ${target_name} output because a temporary file could not be created." >&2
    return 2
  }
  stderr_file=$(mktemp "${TMPDIR:-/tmp}/${HOOK_NAME}.${target_name}.stderr.XXXXXX") || {
    rm -f -- "$stdout_file"
    echo "BLOCKED: ${HOOK_NAME} could not capture ${target_name} output because a temporary file could not be created." >&2
    return 2
  }

  printf '%s' "$INPUT" | "$target" >"$stdout_file" 2>"$stderr_file"
  code=$?
  cat "$stderr_file" >&2
  output=$(cat "$stdout_file")
  rm -f -- "$stdout_file" "$stderr_file"
  if [[ "$code" -ne 0 ]]; then
    return "$code"
  fi

  LAST_HOOK_OUTPUT="$output"
  return 0
}

FIRST_OUTPUT=""
SECOND_OUTPUT=""

run_hook "${SCRIPT_DIR}/ruby-failure-hints.sh" || exit $?
FIRST_OUTPUT="$LAST_HOOK_OUTPUT"

run_hook "${SCRIPT_DIR}/error-critic.sh" || exit $?
SECOND_OUTPUT="$LAST_HOOK_OUTPUT"

if [[ -n "$SECOND_OUTPUT" ]]; then
  printf '%s' "$SECOND_OUTPUT"
elif [[ -n "$FIRST_OUTPUT" ]]; then
  printf '%s' "$FIRST_OUTPUT"
fi
