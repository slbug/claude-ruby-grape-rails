#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail

# Policy: security-sensitive — fail closed when input/payload cannot be inspected.
# Scope: PreToolUse + PermissionRequest + PermissionDenied on Write calls.
# Layer: namespace-containment fallback for the 2 researcher agents that consume
# untrusted WebFetch/WebSearch content. Enforces a per-agent directory allowlist
# (`.claude/research/*`, `.claude/plans/*/research/*` excluding `.provenance.md`).
# Blocks escape from the research namespace, path-traversal, and Writes to
# pre-existing leaves.
#
# NOT a path-pinning defense: within the allowed namespace this hook cannot
# verify the Write target equals the manifest-emitted spawn-prompt path —
# the manifest is not available to hooks. Exact-path enforcement lives in
# each researcher agent's body under "Write boundary (prompt-injection
# defense)". This hook is the second line that prevents namespace escape
# if the agent body clause is bypassed.
#
# Other Write callers (main session, reviewer agents, output-verifier (convo-only,
# no Write), rails-patterns-analyst, etc.) are unaffected — the agent_type gate
# returns exit 0 for any caller outside the scoped set.

SCOPED_AGENT_TYPES=(web-researcher ruby-gem-researcher)

emit_missing_dependency_block() {
  local dependency="$1"

  echo "BLOCKED: block-out-of-bounds-writes.sh cannot inspect the Write target because ${dependency} is unavailable." >&2
  echo "Install the missing dependency or disable the hook explicitly before re-running this Write." >&2
  exit 2
}

command -v jq >/dev/null 2>&1 || emit_missing_dependency_block "jq"
command -v head >/dev/null 2>&1 || emit_missing_dependency_block "head"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || emit_missing_dependency_block "workspace-root-lib.sh"
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"

read_hook_input
INPUT="$HOOK_INPUT_VALUE"
# Mirror block-dangerous-ops.sh: explicitly fail closed on truncated/invalid
# payloads. Empty payload falls through to the downstream tool_name check,
# which fails closed via emit_payload_schema_block (TOOL ends up empty →
# missing-field exit 2). Do NOT add an `empty) exit 0` branch — that would
# fail open and bypass the guardrail.
if [[ -z "$INPUT" ]]; then
  case "${HOOK_INPUT_STATUS:-empty}" in
    truncated|invalid)
      echo "BLOCKED: block-out-of-bounds-writes.sh could not safely inspect hook payload (status: ${HOOK_INPUT_STATUS})." >&2
      echo "Increase RUBY_PLUGIN_MAX_HOOK_INPUT_BYTES or fix the hook input before re-running this Write." >&2
      exit 2
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

# ---------- Per-agent allowlist (segment-boundary aware) ----------
#
# Bash `case` patterns treat `*` as matching any string INCLUDING `/`. Using
# bare `case` globs against the allowlist would let `.claude/research/foo/bar/baz.md`
# match `.claude/research/*/*` (nested deeper) and `.claude/plans/x/y/research/z`
# match `.claude/plans/*/research/*` (extra segments). These helpers validate
# segment counts explicitly so the allowlist matches the documented artifact
# shape and nothing wider.

# .claude/research/<topic-slug>/<aspect-slug>.md  (exactly 2 segments:
# topic dir + aspect file; no nested deeper; no dotfile leading either
# segment to prevent hidden-file forgery; aspect file must be `*.md`).
# Flat .claude/research/<file>.md (consolidated synthesis) is main-session
# territory — researchers MUST NOT write at that level.
match_research_aspect() {
  local rel="$1"
  case "$rel" in
    .claude/research/*/*) ;;
    *) return 1 ;;
  esac
  local after_research="${rel#.claude/research/}"
  local topic="${after_research%%/*}"
  [[ -n "$topic" && "$topic" != */* && "$topic" != .* ]] || return 1
  local tail="${after_research#"$topic"/}"
  [[ -n "$tail" && "$tail" != */* && "$tail" != .* && "$tail" == *.md ]]
}

# .claude/plans/<slug>/research/<file>.md  (slug + file each single segment;
# slug must not start with `.` to refuse `.claude/plans/./research/...`
# and dotfile slug names that would bypass per-plan isolation; file must
# end in `.md` — extensions like `.rb` / `.json` are outside the documented
# research artifact contract).
match_plan_research() {
  local rel="$1"
  case "$rel" in
    .claude/plans/*/research/*) ;;
    *) return 1 ;;
  esac
  local after_plans="${rel#.claude/plans/}"
  local slug="${after_plans%%/*}"
  [[ -n "$slug" && "$slug" != */* && "$slug" != .* ]] || return 1
  local after_slug="${after_plans#"$slug"/}"
  case "$after_slug" in
    research/*) ;;
    *) return 1 ;;
  esac
  local tail="${after_slug#research/}"
  [[ -n "$tail" && "$tail" != */* && "$tail" != .* && "$tail" == *.md ]]
}

# Per-agent map: which segment-bounded matchers apply to which agent.
agent_path_allowed() {
  local agent="$1"
  local rel="$2"
  case "$agent" in
    web-researcher|ruby-gem-researcher)
      # Per-aspect research artifacts only:
      #   .claude/research/<topic-slug>/<aspect-slug>.md (cross-plan)
      #   .claude/plans/<plan-slug>/research/<aspect-slug>.md (plan-local)
      # Provenance sidecars (`*.provenance.md`) are main-session territory
      # (output-verifier is convo-only and returns text; the calling skill body
      # writes the sidecar). Consolidated synthesis at `.claude/research/<slug>.md`
      # is also main-session territory and refused for researcher Writes.
      [[ "$rel" == *.provenance.md ]] && return 1
      match_research_aspect "$rel" || match_plan_research "$rel"
      ;;
    *)
      return 1
      ;;
  esac
}

# ---------- Symlink-ancestor refusal ----------
#
# Bash analogue of `lib/path_safety.rb#reject_symlink_ancestors!` (canonical
# Ruby implementation). Walks lexical components from repo root toward the
# target. Returns 1 if any existing ancestor (or the target itself) is a
# symlink. Stops at the first non-existent component — anything past that
# point cannot have been resolved yet on disk, and the `target_exists`
# check below already refuses pre-existing leaves.
#
# Why bash mirror instead of shelling out to Ruby: hooks fire on every
# Write tool call; Ruby startup latency would tax every guarded write.
# Pattern matches workspace-root-lib.sh which mirrors path_safety.rb
# `canonical_existing_or_deepest` and `path_within_root?` in bash.
reject_symlink_ancestors() {
  local repo_root="$1"
  local abs_target="$2"
  local rel="${abs_target#"$repo_root"}"
  rel="${rel#/}"
  local cur="$repo_root"
  local part
  local IFS='/'
  # shellcheck disable=SC2206 # intentional word-split on slash boundaries
  local parts=($rel)
  for part in "${parts[@]}"; do
    [[ -n "$part" ]] || continue
    cur="${cur}/${part}"
    if [[ -L "$cur" ]]; then
      return 1
    fi
    [[ -e "$cur" ]] || return 0
  done
  return 0
}

# ---------- Response helpers (define before any reject branch) ----------

log_denied_write() {
  local our_reason="$1"
  local logged_path="$2"
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
    --arg canonical "$logged_path" \
    --arg pattern "$our_reason" \
    --arg classifier "$cc_reason" \
    '{ts: now, agent_type: $agent, path: $path, canonical: $canonical, pattern: $pattern, classifier_reason: $classifier}' \
    >> "$target" 2>/dev/null || return 0
}

respond_to_danger() {
  local reason="$1"
  local block_message="$2"
  local logged_path="${3:-}"
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
      log_denied_write "$reason" "$logged_path"
      exit 0
      ;;
    *)
      printf '%s\n' "$block_message" >&2
      exit 2
      ;;
  esac
}

# ---------- Main flow ----------

if [[ "$FILE_PATH" == /* ]]; then
  ABS_TARGET="$FILE_PATH"
else
  ABS_TARGET="${REPO_ROOT%/}/${FILE_PATH#./}"
fi

# Reject path-traversal segments BEFORE prefix/glob checks. Lexical prefix
# match cannot see through `.` / `..` segments. Use respond_to_danger so
# strict-perm mode + denied-jsonl log behave the same as other rejection
# branches. Covers `/../` (parent-traversal), trailing `/..`, `/./`
# (no-op segment that skips per-plan slug), and trailing `/.`.
case "$ABS_TARGET" in
  *'/../'*|*'/..'|*'/./'*|*'/.')
    respond_to_danger "path_traversal" \
      "BLOCKED: ${AGENT_TYPE} attempted to Write with a path-traversal segment: ${FILE_PATH}." \
      "$ABS_TARGET"
    ;;
esac

# Lexical containment check — pure string prefix, NO disk probe. Must run
# before any `-d` / `cd` / canonicalization on user-controlled path
# components. Probing parent dirs of outside-repo targets first would
# leak whether those paths exist (or where symlinks resolve to) via the
# denial message, turning denied Writes into a filesystem-existence
# oracle for /etc, $HOME, etc. REPO_ROOT is already canonicalized by
# `resolve_workspace_root`. ABS_TARGET is the raw lexical absolute path.
case "$ABS_TARGET" in
  "${REPO_ROOT}/"*|"$REPO_ROOT") ;;
  *)
    respond_to_danger "out_of_repo" \
      "BLOCKED: ${AGENT_TYPE} attempted to Write outside the repo root: ${ABS_TARGET}." \
      "$ABS_TARGET"
    ;;
esac

# Refuse if any ancestor on the lexical path resolves to a symlink — catches
# `.claude` (or any intermediate dir) symlinked to a location outside the
# repo even when the leaf directory does not yet exist. Walk constrained to
# repo_root; only probes within-repo paths.
if ! reject_symlink_ancestors "$REPO_ROOT" "$ABS_TARGET"; then
  respond_to_danger "symlinked_ancestor" \
    "BLOCKED: ${AGENT_TYPE} attempted to Write through a symlinked ancestor in: ${ABS_TARGET}. Refusing (symlink-attack defense)." \
    "$ABS_TARGET"
fi

# Canonical target for logging + allowlist check. Safe to canonicalize
# now: lexical containment above already guaranteed the target is inside
# repo_root; canonicalization only probes within-repo paths.
parent_dir=$(path_dirname "$ABS_TARGET") || parent_dir=""
if [[ -n "$parent_dir" && -d "$parent_dir" ]]; then
  canonical_parent=$(cd "$parent_dir" >/dev/null 2>&1 && pwd -P) || canonical_parent="$parent_dir"
else
  canonical_parent="$parent_dir"
fi
base=$(path_basename "$ABS_TARGET") || base=""
canonical_target="${canonical_parent%/}/${base}"

canonical_root=$(cd "$REPO_ROOT" >/dev/null 2>&1 && pwd -P) || canonical_root="$REPO_ROOT"

relative_target="${canonical_target#"${canonical_root}/"}"
if ! agent_path_allowed "$AGENT_TYPE" "$relative_target"; then
  respond_to_danger "out_of_allowlist" \
    "BLOCKED: ${AGENT_TYPE} attempted to Write to a path outside its per-agent allowlist: ${canonical_target}." \
    "$canonical_target"
fi

# Fresh-write contract for scoped researchers. CC subagent Edit is broken
# (cannot update existing files at all), and CC subagent Write also has
# known reliability issues on existing paths. Defense: every scoped Write
# goes to a non-existing target. Research artifact paths are stable
# (`{topic-slug}.md`); the existence guard forces researchers to fail loud
# when a previous artifact already lives at the same path so the main
# session can rotate the run rather than silently dropping a Write.
# Covers regular file, directory, AND pre-symlinked-target attack at the leaf.
if [[ -e "$ABS_TARGET" ]] || [[ -L "$ABS_TARGET" ]]; then
  respond_to_danger "target_exists" \
    "BLOCKED: ${AGENT_TYPE} attempted to Write an existing target: ${ABS_TARGET}. Scoped Write targets must be non-existing (CC subagent Edit/Write cannot update existing files reliably). Rotate to a fresh path." \
    "$ABS_TARGET"
fi

exit 0
