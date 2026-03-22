#!/usr/bin/env bash
set -o nounset
set -o pipefail

# GENERATED FROM iron-laws.yml — DO NOT EDIT
# Last generated: 2026-03-22T21:06:02Z

command -v jq >/dev/null 2>&1 || exit 0

additional_context=$(cat <<'EOF'
Ruby/Rails/Grape Iron Laws (NON-NEGOTIABLE) — 21 Total:

Active Record (7):
Sidekiq (4):
Security (4):
Ruby (3):
Hotwire/Turbo (2):
Verification (1):

Iron Law 1: NEVER use float for money — use decimal or integer cents
Iron Law 2: ALWAYS use parameterized queries — never SQL string interpolation
Iron Law 3: USE includes/preload for associations — never N+1 queries
Iron Law 4: CALL after_commit not after_save when enqueueing jobs
Iron Law 5: WRAP multi-step operations in ActiveRecord::Base.transaction
Iron Law 6: NO update_columns or save(validate: false) in normal flows
Iron Law 7: NO default_scope — use explicit named scopes only
Iron Law 8: Jobs MUST be idempotent — safe to retry
Iron Law 9: Args use JSON-safe types only — no symbols, no Ruby objects, no procs
Iron Law 10: NEVER store ActiveRecord objects in args — store IDs, not records
Iron Law 11: ALWAYS use after_commit callback — not after_save or inline
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
EOF
)

jq -n --arg ctx "$additional_context" '{"hookSpecificOutput": {"hookEventName": "SubagentStart", "additionalContext": $ctx}}'
