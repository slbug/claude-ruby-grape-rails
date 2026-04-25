#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: advisory — warn/skip on degraded state, exit 0.


HOOK_NAME="${BASH_SOURCE[0]##*/}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

emit_missing_dependency_block() {
  local dependency="$1"
  echo "BLOCKED: ${HOOK_NAME} cannot inspect the hook payload because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before continuing." >&2
  exit 2
}

# Source workspace-root-lib.sh for read_hook_input helper
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"

# Read hook input with size validation and JSON checking
read_hook_input
INPUT="${HOOK_INPUT_VALUE:-}"
case "${HOOK_INPUT_STATUS:-empty}" in
  truncated|invalid)
    if [[ "${HOOK_INPUT_STATUS}" == "invalid" ]]; then
      echo "BLOCKED: ${HOOK_NAME} could not safely inspect an invalid hook payload." >&2
    else
      echo "BLOCKED: ${HOOK_NAME} could not safely inspect a truncated hook payload." >&2
    fi
    echo "Fix the hook input before retrying delegated Ruby failure diagnostics." >&2
    exit 2
    ;;
esac
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

  if ! command -v mktemp >/dev/null 2>&1; then
    echo "BLOCKED: ${HOOK_NAME} cannot run ${target_name} because mktemp is unavailable." >&2
    echo "Install mktemp before retrying the failed Ruby command." >&2
    return 2
  fi

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
