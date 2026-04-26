#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Policy: advisory PostToolUse hook. Telemetry collector — opt-in via
# RUBY_PLUGIN_COMPRESSION_TELEMETRY=1. When enabled, appends compression
# stats to ${CLAUDE_PLUGIN_DATA}/compression.jsonl and preserves raw
# stdout under ${CLAUDE_PLUGIN_DATA}/verify-raw/<uuid>.log for the user
# (and, if the user chooses to share, plugin contributors). When disabled
# (default), the hook exits 0 immediately and writes nothing to disk.
# Does NOT replace Bash tool stdout: per Anthropic Claude Code hooks docs,
# PostToolUse stdout is written to the debug log (transcript exceptions are
# UserPromptSubmit / UserPromptExpansion / SessionStart only), and the
# PostToolUse decision-control fields layer additional context rather than
# replacing tool output for non-MCP tools. A real replacement mechanism is
# deferred until telemetry quantifies real-world ratios. Hook is fail-open:
# missing ruby, missing CLI binaries, or unreadable rules cause a clean
# exit 0 — raw Bash output is preserved unchanged.

# Opt-in. Default off — telemetry is only written when the user explicitly
# sets the env var. Keeps the plugin privacy-respecting by default.
[[ "${RUBY_PLUGIN_COMPRESSION_TELEMETRY:-0}" == "1" ]] || exit 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
[[ "${HOOK_INPUT_STATUS:-empty}" == "valid" ]] || exit 0

PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-}"
[[ -n "$PLUGIN_ROOT" ]] || exit 0

# Fail-open: missing jq → exit silently. PostToolUse stderr feeds messages
# back to Claude, so a `jq: command not found` slipping through would
# violate the documented fail-open contract.
command -v jq >/dev/null 2>&1 || exit 0

TOOL_NAME="$(printf '%s' "$HOOK_INPUT_VALUE" | jq -r '.tool_name // empty' 2>/dev/null)"
[[ "$TOOL_NAME" == "Bash" ]] || exit 0
COMMAND="$(printf '%s' "$HOOK_INPUT_VALUE" | jq -r '.tool_input.command // empty' 2>/dev/null)"
STDOUT="$(printf '%s' "$HOOK_INPUT_VALUE" | jq -r '.tool_response.output // empty' 2>/dev/null)"
[[ -n "$COMMAND" && -n "$STDOUT" ]] || exit 0

TRIGGERS="${PLUGIN_ROOT}/references/compression/triggers.yml"
[[ -r "$TRIGGERS" ]] || exit 0

# Fail-open: if ruby is unavailable or CLI binaries missing, exit silently.
command -v ruby >/dev/null 2>&1 || exit 0

MATCHER="${PLUGIN_ROOT}/bin/match-trigger"
CLI="${PLUGIN_ROOT}/bin/compress-verify"
[[ -x "$MATCHER" && -x "$CLI" ]] || exit 0

# match-trigger exit codes: 0 = matched (proceed); any non-zero = either
# "no match" / "excluded by rake_excluded" / "loader error" — these are
# not distinguished by the CLI, and the hook treats them all as "skip".
"$MATCHER" --triggers "$TRIGGERS" --cmd "$COMMAND" || exit 0

[[ -n "${CLAUDE_PLUGIN_DATA:-}" ]] || exit 0
DATA_DIR="$CLAUDE_PLUGIN_DATA"
mkdir -p "${DATA_DIR}/verify-raw"
UUID="$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null || date +%s%N)"
RAW_LOG="${DATA_DIR}/verify-raw/${UUID}.log"
printf '%s' "$STDOUT" > "$RAW_LOG"

printf '%s' "$STDOUT" | "$CLI" \
  --log "${DATA_DIR}/compression.jsonl" \
  --cmd "$COMMAND" \
  --raw-log "$RAW_LOG" || true
exit 0
