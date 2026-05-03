#!/usr/bin/env bash
set -o nounset
set -o pipefail

# Inject Iron Laws + Advisory Preferences via additionalContext.
# Wired in hooks.json under both SessionStart (main-session) and
# SubagentStart (per-subagent). Reads hook_event_name from input,
# echoes it back in hookSpecificOutput.hookEventName per CC schema.
# Policy: advisory injection; emit-then-exit. Failure to emit
# leaves the receiver without injected context — fail-open by
# design, no guardrail semantics.
# GENERATED FROM iron-laws.yml + preferences.yml — DO NOT EDIT
# Source versions: iron-laws=1.0.0 preferences=1.1.0

# End-user opt-out: skip injection entirely. Useful when the plugin
# is installed at user scope but the active project is not Ruby/Rails/
# Grape. Set per shell, per-command, or via direnv (.envrc).
[[ "${RUBY_PLUGIN_DISABLE_RULES_INJECTION:-0}" == "1" ]] && exit 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_LIB="${SCRIPT_DIR}/workspace-root-lib.sh"
[[ -r "$ROOT_LIB" && ! -L "$ROOT_LIB" ]] || exit 0
# shellcheck disable=SC1090,SC1091
source "$ROOT_LIB"
read_hook_input

# Need jq to construct the JSON output safely.
command -v jq >/dev/null 2>&1 || exit 0

# Echo the firing event name back per CC output convention.
EVENT=""
[[ "${HOOK_INPUT_STATUS:-empty}" == "valid" ]] && \
  EVENT="$(printf "%s" "$HOOK_INPUT_VALUE" | jq -r ".hook_event_name // empty" 2>/dev/null || true)"
[[ -n "$EVENT" ]] || exit 0

BODY=$(cat <<'RULES_BODY_EOF'
Ruby/Rails/Grape Iron Laws (NON-NEGOTIABLE) — 22 Total:

Active Record (7):
Sidekiq (4):
Security (4):
Ruby (3):
Hotwire/Turbo (2):
Verification & Discipline (2):

Iron Law 1: NEVER use float for money — use decimal or integer cents
Iron Law 2: ALWAYS use parameterized queries — never SQL string interpolation
Iron Law 3: USE includes/preload for associations — never N+1 queries
Iron Law 4: IN Active Record code, use after_commit not after_save when enqueueing jobs
Iron Law 5: WRAP multi-step operations in ActiveRecord::Base.transaction
Iron Law 6: NO update_columns or save(validate: false) in normal flows
Iron Law 7: NO default_scope — use explicit named scopes only
Iron Law 8: Jobs MUST be idempotent — safe to retry
Iron Law 9: Args use JSON-safe types only — no symbols, no Ruby objects, no procs
Iron Law 10: NEVER store ORM objects in args — store IDs, not records
Iron Law 11: ALWAYS enqueue jobs after commit using the active ORM or transaction hook
Iron Law 12: NO eval with user input — code injection vulnerability
Iron Law 13: AUTHORIZE in EVERY controller action — do not trust before_action alone
Iron Law 14: NEVER use html_safe or raw with untrusted content — XSS vulnerability
Iron Law 15: NO SQL string concatenation — always use parameterized queries
Iron Law 16: NO method_missing without respond_to_missing? — breaks introspection
Iron Law 17: SUPERVISE ALL BACKGROUND PROCESSES — use proper process managers
Iron Law 18: DON'T RESCUE Exception — only rescue StandardError or specific classes
Iron Law 19: NEVER query DB in Turbo Stream responses — pre-compute everything
Iron Law 20: ALWAYS use turbo_frame_tag for partial updates
Iron Law 21: VERIFY BEFORE CLAIMING DONE — never say 'should work' — run tests and show results
Iron Law 22: SURGICAL CHANGES ONLY — every changed line must trace to the user's request. Don't improve adjacent code.

Advisory Preferences — 5 Total:
Preference: PREFER Context7 MCP (`mcp__*context7*__query-docs` / `resolve-library-id`) over WebFetch for library/gem docs — fallback to WebFetch only if Context7 tools unavailable
Preference: CHALLENGE false user premises before executing. If request contradicts repo evidence, surface the conflict before proceeding.
Preference: AVOID unsupported agreement, apology cascades, and hedge chains. Acknowledge mistakes once, continue. Direct language for HIGH-confidence findings.
Preference: PREFER positive success targets over prohibition chains in task instructions and success criteria.
Preference: ALWAYS use the `Grep` tool over shell `grep`/`rg`/`ag`, the `Glob` tool over `find`/`ls`, and `Read` over `cat`/`head`/`tail`. Batch `git diff`/`git log`/gem inspection by path group, never per-item loops. Exclude high-noise paths (cassettes, fixtures, lockfiles) via pathspec. Per-file allowed when the file is the unit of investigation.
RULES_BODY_EOF
)

jq -nc --arg ev "$EVENT" --arg ctx "$BODY" \
  '{hookSpecificOutput:{hookEventName:$ev,additionalContext:$ctx}}'
