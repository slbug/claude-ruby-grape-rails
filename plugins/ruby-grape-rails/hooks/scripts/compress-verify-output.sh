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

# Verify-output telemetry's whole point is the LARGE outputs (full rspec
# runs, brakeman scans). The default 256 KiB cap in `read_hook_input`
# would systematically drop those, so raise it for this hook unless the
# user already overrode it. 8 MiB covers ~150K-line rspec output.
export RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES="${RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES:-8388608}"

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

# Single jq pass extracts the small metadata (tool_name + command),
# NUL-delimited, into shell vars. The large `tool_response.output`
# field is streamed to a file later — never captured into a shell
# variable, where command substitution would strip trailing newlines
# and force the whole payload into memory.
TOOL_NAME=""
COMMAND=""
{
  IFS= read -r -d '' TOOL_NAME || true
  IFS= read -r -d '' COMMAND || true
} < <(printf '%s' "$HOOK_INPUT_VALUE" \
        | jq -j '(.tool_name // "") + "\u0000" + (.tool_input.command // "") + "\u0000"' \
          2>/dev/null)
[[ "$TOOL_NAME" == "Bash" ]] || exit 0
[[ -n "$COMMAND" ]] || exit 0

TRIGGERS="${PLUGIN_ROOT}/references/compression/triggers.yml"
RULES="${PLUGIN_ROOT}/references/compression/rules.yml"
# Preflight both config files BEFORE writing any telemetry. An
# unreadable rules.yml during the compressor stage would still produce
# a JSONL entry (the Ruby loader rescues to an empty ruleset), but it
# would also write a raw log without a fully-validated config — better
# to bail here so the user's data dir stays consistent.
[[ -r "$TRIGGERS" ]] || exit 0
[[ -r "$RULES" ]] || exit 0

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
# Refuse to write through a symlinked plugin-data dir: a manipulated
# env var pointing CLAUDE_PLUGIN_DATA at a symlink to an unrelated
# directory would otherwise let this hook materialize files outside
# the plugin-owned tree. Mirrors the symlink guards used elsewhere
# in this repo's hook scripts (workspace-root-lib.sh and friends).
[[ -d "$DATA_DIR" && ! -L "$DATA_DIR" ]] || exit 0

RAW_DIR="${DATA_DIR}/verify-raw"
# `mkdir -p` is a no-op if RAW_DIR already exists. After the call
# verify it is a real directory (not a pre-existing symlink to
# elsewhere) before any writes land underneath it.
mkdir -p "$RAW_DIR"
[[ -d "$RAW_DIR" && ! -L "$RAW_DIR" ]] || exit 0

# UUID via Ruby stdlib `SecureRandom.uuid`. The previous fallback chain
# (`uuidgen` → `/proc/sys/kernel/random/uuid` → `date +%s%N`) was not
# portable: BSD/macOS `date` ignores `%N` and emits a literal `N`, so
# concurrent invocations would collide on the same RAW_LOG path. Ruby
# is already a hard dependency at this point. The basename shape is
# also constrained to the SecureRandom.uuid output so a malformed UUID
# can never escape RAW_DIR via path traversal.
UUID="$(ruby -rsecurerandom -e 'puts SecureRandom.uuid' 2>/dev/null)"
[[ "$UUID" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || exit 0
RAW_LOG="${RAW_DIR}/${UUID}.log"

# Stream `tool_response.output` from the hook payload directly to the
# raw-log file via a SECOND jq pass (one for metadata above, one for
# the body here — total 2 jq invocations vs the original 3). `-j`
# emits the raw string with no trailing newline jq would otherwise
# append, so byte counts match the original Bash output exactly.
#
# The plugin never `rm`s a user-visible telemetry file itself: that is
# the user's data, the status-advisory hook surfaces accumulation, and
# the user runs `rm` themselves when they decide to clean up. So a
# partial / empty / errored write here just leaves whatever bytes
# landed on disk; an early `exit 0` skips the JSONL entry and the
# leftover raw log is treated like any other accumulated telemetry.
# Stream into RAW_LOG via Ruby with `O_CREAT | O_EXCL | O_NOFOLLOW`
# rather than shell `>`. EXCL refuses to clobber a pre-existing file
# at the UUID path (collision is cryptographically improbable but
# defense-in-depth); NOFOLLOW refuses to follow a symlink there. Mode
# 0o600 keeps raw outputs readable only by the owner — these capture
# whatever the user's verify command emitted, which can include
# project-internal data.
# shellcheck disable=SC2016  # Ruby script body uses Ruby interpolation, not shell expansion
printf '%s' "$HOOK_INPUT_VALUE" \
  | jq -j '.tool_response.output // ""' 2>/dev/null \
  | ruby -e '
      flags = File::WRONLY | File::CREAT | File::EXCL | File::NOFOLLOW
      $stdin.binmode
      File.open(ARGV[0], flags, 0o600) { |out| IO.copy_stream($stdin, out) }
    ' "$RAW_LOG" 2>/dev/null || exit 0
[[ -s "$RAW_LOG" ]] || exit 0

# Compressor reads the raw output from stdin (redirect from RAW_LOG)
# and records the RAW_LOG path string into the JSONL entry's `raw_log`
# field via the `--raw-log` flag. The CLI never writes to RAW_LOG —
# the same path appearing in both positions is read-only. On
# compressor failure the JSONL entry simply does not get appended and
# the raw log stays on disk for the user to inspect (or clean up).
# stderr is redirected to /dev/null: PostToolUse stderr feeds messages
# back to Claude, and a Ruby exception or OptionParser error from the
# CLI escaping into the transcript would violate the documented
# fail-open contract.
# shellcheck disable=SC2094  # --raw-log is a path-string flag, not a write target
"$CLI" \
  --log "${DATA_DIR}/compression.jsonl" \
  --cmd "$COMMAND" \
  --raw-log "$RAW_LOG" \
  < "$RAW_LOG" 2>/dev/null || true
exit 0
