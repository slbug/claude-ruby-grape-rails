#!/usr/bin/env bash
# Shared timeout helper for hook scripts.
# Resolves timeout -> gtimeout -> no-timeout fallback for macOS compatibility.
# Source this file, then call: run_with_timeout <seconds> <command...>

# Resolve timeout command (macOS ships without `timeout`; coreutils provides `gtimeout`).
if command -v timeout >/dev/null 2>&1; then
  TIMEOUT_CMD="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_CMD="gtimeout"
else
  TIMEOUT_CMD=""
fi

# Run command with timeout if available, otherwise run directly.
run_with_timeout() {
  local secs="$1"; shift
  if [[ -n "$TIMEOUT_CMD" ]]; then
    "$TIMEOUT_CMD" "$secs" "$@"
  else
    "$@"
  fi
}
