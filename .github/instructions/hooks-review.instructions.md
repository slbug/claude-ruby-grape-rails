---
applyTo: "**/*.sh"
excludeAgent: "coding-agent"
---

# Shell Script and Hook Review Rules

## Shell Hardening

- All executable hook scripts must use `set -o nounset` and `set -o pipefail`
- Library files (`*-lib.sh`) sourced by other scripts may omit these since
  the caller's settings apply
- Do NOT add `set -e` / `set -o errexit` unless the script must abort on
  any failure (only block-dangerous-ops.sh and active-plan-marker.sh use it).
  Most hooks intentionally handle failures gracefully — advisory hooks
  warn/skip, guardrails fail closed via explicit checks, not errexit
- Use `command -v` to check for dependencies (jq, grep, etc) before use
- Use `${var:?}` in deletion commands to prevent empty-variable disasters
- Each script should have a `# Policy:` comment near the top documenting
  its failure behavior (advisory, fail-closed, or security-sensitive)
- Use `read_hook_input` from workspace-root-lib.sh for stdin JSON parsing
- Use `resolve_workspace_root` for safe repo root resolution

## Deletion Safety

- `rm -f` only for `mktemp` outputs or exact fixed plugin-owned paths
- `rm -rf` only for validated `mktemp -d` outputs
- `rmdir` for expected-empty lock directories
- For variable-based cleanup, validate the path/prefix first

## Hook Output Patterns

- PostToolUse stdout is verbose-mode only — use `exit 2` + stderr to feed
  messages to Claude
- SessionStart stdout IS added to Claude's context
- SubagentStart uses `hookSpecificOutput.additionalContext`
- SubagentStop logs metrics asynchronously — always exits 0
- PostToolUseFailure uses `hookSpecificOutput.additionalContext`
- PreCompact uses stderr for context reminders; exit 2 blocks compaction
  during active work/full phases

## Hook Failure Policy

Each script must document its failure policy near the top:

- **Advisory hooks** (detect-runtime, check-resume, log-progress): warn or
  skip on degraded state
- **Delegated Ruby guardrails** (rubyish-post-edit, format-ruby, verify-ruby,
  debug-statement-warning): fail closed once selected for a Ruby path
- **Security-sensitive hooks** (secret-scan, block-dangerous-ops): fail
  closed in strict/high-confidence cases

## Configurable Timeouts

Hook scripts wrap slow sub-commands with `timeout` and env var overrides:

- `RUBY_PLUGIN_FORMATTER_TIMEOUT` (default 120s) — format-ruby.sh
- `RUBY_PLUGIN_RUBY_CHECK_TIMEOUT` (default 30s) — verify-ruby.sh
- `RUBY_PLUGIN_BETTERLEAKS_TIMEOUT` (default 60s) — secret-scan.sh
- `RUBY_PLUGIN_DETECT_STACK_TIMEOUT` (default 15s) — detect-runtime.sh

Exit code 124 from `timeout`/`gtimeout` is handled explicitly:

- **Delegated guardrails** (format-ruby, verify-ruby): fail closed (exit 2)
  with remediation hint to raise the env var
- **Security hooks** (secret-scan): fail closed (exit 2)
- **Advisory hooks** (detect-runtime): skip and continue

Scripts resolve `timeout` → `gtimeout` → no-timeout fallback via
`run_with_timeout()` for macOS compatibility.

## Do NOT Flag

- `exit 2` is intentional (feeds stderr to Claude, not an error)
- `jq -r '... // empty'` fallback patterns are intentional null-safety
- `HOOK_INPUT_VALUE` and `HOOK_NAME` variables from sourced libraries
- `workspace-root-lib.sh` sourcing pattern
- Long case statements in block-dangerous-ops.sh (necessary coverage)
- `run_with_timeout` / `timeout` / `gtimeout` wrapping external commands
- `TIMEOUT_CMD` resolution pattern (timeout → gtimeout → empty fallback)
- `RUBY_PLUGIN_*` env var defaults via `${VAR:-default}` syntax
