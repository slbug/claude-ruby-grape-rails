#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

# Policy: security-sensitive — fail closed when input/payload cannot be inspected.
# Scope: PreToolUse + PermissionRequest + PermissionDenied on Write calls.
# Enforces a per-agent path allowlist for the 3 research/verification agents
# that consume untrusted WebFetch/WebSearch content (and, for output-verifier,
# untrusted draft artifacts). Defense in depth against prompt-injection that
# tries to redirect Write to filesystem paths outside research output.
#
# Other Write callers (main session, reviewer agents, rails-patterns-analyst,
# active-record-schema-designer, etc.) are unaffected — agent_type gate at
# top of script returns exit 0 for any caller outside the scoped set.

SCOPED_AGENT_TYPES=(web-researcher ruby-gem-researcher output-verifier)
# Allowed Write patterns (case-glob, relative to repo root). Tighter than
# bare-prefix allowlist: plan namespace is constrained to the per-plan
# research/ subtree, and review namespace is constrained to provenance
# sidecars at the consolidated-review path (the only output-verifier
# product). Anything else under .claude/plans/<slug>/ or .claude/reviews/
# (scratchpad, plan.md, per-reviewer artifacts, etc.) belongs to other
# agents or main-session writes and is refused for the 3 scoped agents.
ALLOWED_WRITE_PATTERNS=(
  ".claude/research/*"
  ".claude/plans/*/research/*"
  ".claude/reviews/*.provenance.md"
)

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: block-out-of-bounds-writes.sh cannot inspect the Write target because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before re-running this Write." >&2
  exit 2
}

command -v jq >/dev/null 2>&1 || emit_missing_dependency_block "jq"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"

read_hook_input
INPUT="$HOOK_INPUT_VALUE"
if [[ -z "$INPUT" ]]; then
  case "${HOOK_INPUT_STATUS:-empty}" in
    truncated|invalid)
      echo "BLOCKED: block-out-of-bounds-writes.sh could not safely inspect a ${HOOK_INPUT_STATUS} hook payload." >&2
      echo "Increase RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES or fix the hook input before re-running this Write." >&2
      exit 2
      ;;
    empty)
      exit 0
      ;;
  esac
fi

emit_payload_schema_block() {
  local reason="$1"

  echo "BLOCKED: block-out-of-bounds-writes.sh could not safely inspect the Write target because ${reason}." >&2
  echo "Fix the hook payload schema before re-running this Write." >&2
  exit 2
}

TOOL=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null) || emit_payload_schema_block "tool_name could not be parsed"
[[ -n "$TOOL" ]] || emit_payload_schema_block "tool_name was missing"
[[ "$TOOL" == "Write" ]] || exit 0

AGENT_TYPE=$(printf '%s' "$INPUT" | jq -r '.agent_type // empty' 2>/dev/null || true)
# No agent_type → main-session call → pass (out of scope for this hook).
[[ -n "$AGENT_TYPE" ]] || exit 0

agent_scoped=0
for scoped in "${SCOPED_AGENT_TYPES[@]}"; do
  if [[ "$AGENT_TYPE" == "$scoped" ]]; then
    agent_scoped=1
    break
  fi
done
[[ "$agent_scoped" -eq 1 ]] || exit 0

FILE_PATH=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null) || emit_payload_schema_block "tool_input.file_path could not be parsed"
[[ -n "$FILE_PATH" ]] || emit_payload_schema_block "tool_input.file_path was missing"

REPO_ROOT="$(resolve_workspace_root "$INPUT" 2>/dev/null || true)"
[[ -n "$REPO_ROOT" ]] || emit_payload_schema_block "workspace root could not be resolved"

# Event-name routes danger response (mirrors block-dangerous-ops.sh):
#   PreToolUse / unset  → hard block (exit 2 + stderr)
#   PermissionRequest   → structured JSON deny
#   PermissionDenied    → log denial, exit 0
EVENT=$(printf '%s' "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null || true)

# Compute target absolute path. Per plugin convention (and CC subagent
# overwrite-bug workaround) the target MUST NOT exist: prepare-respawn rotates
# any prior file before spawn. Existing target → refuse (covers regular file,
# directory, symlink, and pre-symlinked-target attack in one check).
if [[ "$FILE_PATH" == /* ]]; then
  ABS_TARGET="$FILE_PATH"
else
  ABS_TARGET="${REPO_ROOT%/}/${FILE_PATH#./}"
fi

# Reject path-traversal segments (`/../` anywhere, or trailing `/..`). Lexical
# prefix check below cannot see through `..`, so refuse before computing the
# canonical target. Legitimate filenames containing `..` without surrounding
# slashes (e.g. `foo..bar.md`) are not affected.
case "$ABS_TARGET" in
  *'/../'*|*'/..')
    EVENT=$(printf '%s' "$INPUT" | jq -r '.hook_event_name // empty' 2>/dev/null || true)
    case "$EVENT" in
      PermissionRequest)
        jq -nc --arg msg "BLOCKED: ${AGENT_TYPE} attempted to Write with a path-traversal segment: ${FILE_PATH}." \
          '{ hookSpecificOutput: { hookEventName: "PermissionRequest", decision: { behavior: "deny", message: $msg, interrupt: false } } }'
        exit 0
        ;;
      PermissionDenied)
        exit 0
        ;;
      *)
        echo "BLOCKED: ${AGENT_TYPE} attempted to Write with a path-traversal segment: ${FILE_PATH}." >&2
        exit 2
        ;;
    esac
    ;;
esac

target_exists=0
{ [[ -e "$ABS_TARGET" ]] || [[ -L "$ABS_TARGET" ]]; } && target_exists=1

parent_dir=$(path_dirname "$ABS_TARGET") || parent_dir=""
if [[ -n "$parent_dir" && -d "$parent_dir" ]]; then
  canonical_parent=$(cd "$parent_dir" >/dev/null 2>&1 && pwd -P) || canonical_parent="$parent_dir"
else
  canonical_parent="$parent_dir"
fi
base=$(path_basename "$ABS_TARGET") || base=""
canonical_target="${canonical_parent%/}/${base}"

canonical_root=$(cd "$REPO_ROOT" >/dev/null 2>&1 && pwd -P) || canonical_root="$REPO_ROOT"

log_denied_write() {
  local our_reason="$1"
  local data_dir="${CLAUDE_PLUGIN_DATA:-}"
  [[ -n "$data_dir" ]] || return 0
  [[ -L "$data_dir" ]] && return 0
  mkdir -p "$data_dir" 2>/dev/null || return 0
  local target="${data_dir}/denied-writes.jsonl"
  [[ -L "$target" ]] && return 0
  local cc_reason=""
  cc_reason="$(printf '%s' "$INPUT" | jq -r '.reason // empty' 2>/dev/null || true)"
  jq -nc \
    --arg agent "$AGENT_TYPE" \
    --arg path "$FILE_PATH" \
    --arg canonical "$canonical_target" \
    --arg pattern "$our_reason" \
    --arg classifier "$cc_reason" \
    '{ts: now, agent_type: $agent, path: $path, canonical: $canonical, pattern: $pattern, classifier_reason: $classifier}' \
    >> "$target" 2>/dev/null || return 0
}

respond_to_danger() {
  local reason="$1"
  local block_message="$2"
  local interrupt="false"
  case "$EVENT" in
    PermissionRequest)
      [[ "${RUBY_PLUGIN_STRICT_PERMS:-0}" == "1" ]] && interrupt="true"
      jq -nc \
        --arg msg "$block_message" \
        --argjson interrupt "$interrupt" \
        '{
          hookSpecificOutput: {
            hookEventName: "PermissionRequest",
            decision: { behavior: "deny", message: $msg, interrupt: $interrupt }
          }
        }'
      exit 0
      ;;
    PermissionDenied)
      log_denied_write "$reason"
      exit 0
      ;;
    *)
      printf '%s\n' "$block_message" >&2
      exit 2
      ;;
  esac
}

if [[ "$target_exists" -eq 1 ]]; then
  respond_to_danger "target_exists" \
    "BLOCKED: ${AGENT_TYPE} attempted to Write an existing target: ${ABS_TARGET}. Per plugin convention (CC subagent overwrite-bug workaround) Write targets must be non-existing. Main session calls prepare-respawn to rotate prior files before re-spawn."
fi

if [[ "$canonical_target" != "${canonical_root}/"* ]]; then
  respond_to_danger "out_of_repo" \
    "BLOCKED: ${AGENT_TYPE} attempted to Write outside the repo root: ${canonical_target}. Allowed patterns (relative to repo root): ${ALLOWED_WRITE_PATTERNS[*]}."
fi

relative_target="${canonical_target#"${canonical_root}/"}"
pattern_match=0
for pattern in "${ALLOWED_WRITE_PATTERNS[@]}"; do
  # shellcheck disable=SC2254 # intentional glob match against fixed pattern set
  case "$relative_target" in
    $pattern) pattern_match=1; break ;;
  esac
done

if [[ "$pattern_match" -ne 1 ]]; then
  respond_to_danger "out_of_allowlist" \
    "BLOCKED: ${AGENT_TYPE} attempted to Write to a path outside its research-output allowlist: ${canonical_target}. Allowed patterns (relative to repo root): ${ALLOWED_WRITE_PATTERNS[*]}."
fi

exit 0
