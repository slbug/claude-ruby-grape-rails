#!/usr/bin/env bash
set -o nounset
set -o pipefail

# SubagentStop hook: Log agent metrics to JSONL for observability.
# Policy: advisory async hook; never blocks subagent stop (always exit 0).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input
INPUT="$HOOK_INPUT_VALUE"
if [[ -z "$INPUT" ]]; then
  exit 0
fi

# Extract fields from hook payload (jq pattern matches existing hooks)
command -v jq >/dev/null 2>&1 || exit 0
AGENT_ID=$(printf '%s' "$INPUT" | jq -r '.agent_id // empty' 2>/dev/null)
AGENT_TYPE=$(printf '%s' "$INPUT" | jq -r '.agent_type // empty' 2>/dev/null)

if [[ -z "$AGENT_ID" && -z "$AGENT_TYPE" ]]; then
  exit 0
fi

# Write to plugin data dir if available, else workspace .claude/
METRICS_DIR="${CLAUDE_PLUGIN_DATA:-}"
if [[ -z "$METRICS_DIR" ]]; then
  METRICS_DIR="$(resolve_workspace_root 2>/dev/null)/.claude" || exit 0
fi
[[ -d "$METRICS_DIR" && ! -L "$METRICS_DIR" ]] || exit 0

METRICS_FILE="${METRICS_DIR}/.agent_metrics.jsonl"
[[ ! -L "$METRICS_FILE" ]] || exit 0

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

jq -n --arg ts "$TIMESTAMP" --arg id "$AGENT_ID" --arg type "$AGENT_TYPE" \
  '{ts: $ts, agent_id: $id, agent_type: $type}' >> "$METRICS_FILE" 2>/dev/null

exit 0
