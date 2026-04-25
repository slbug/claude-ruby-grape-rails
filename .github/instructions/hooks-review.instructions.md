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

Each script must document its failure policy near the top. Current
classification of shipped hooks under
`plugins/ruby-grape-rails/hooks/scripts/`:

- **Advisory hooks** (warn/skip, exit 0 on degraded state):
  `detect-runtime.sh`, `detect-runtime-async.sh`, `detect-runtime-fast.sh`,
  `detect-runtime-file-changed.sh`, `check-resume.sh`,
  `check-scratchpad.sh`, `check-pending-plans.sh`,
  `check-plugin-version.sh`, `log-progress.sh`,
  `log-subagent-metrics.sh`, `session-title.sh`, `setup-dirs.sh`,
  `install-statusline-wrapper.sh`, `stop-failure-log.sh`,
  `plan-stop-reminder.sh`, `postcompact-verify.sh`,
  `precompact-rules.sh`, `security-reminder.sh`,
  `ruby-failure-hints.sh`, `ruby-post-tool-use-failure.sh`,
  `error-critic.sh`
- **Delegated Ruby guardrails** (fail closed once selected for a
  Ruby path): `rubyish-post-edit.sh`, `format-ruby.sh`,
  `verify-ruby.sh`, `debug-statement-warning.sh`
- **Security-sensitive hooks** (fail closed in strict/high-confidence
  cases): `secret-scan.sh`, `block-dangerous-ops.sh`,
  `iron-law-verifier.sh`
- **Generated injector** (do NOT hand-edit): `inject-iron-laws.sh` is
  rebuilt from `references/iron-laws.yml` + `preferences.yml` by
  `scripts/generate-iron-law-outputs.sh`. Header carries
  `Source versions: iron-laws=<v> preferences=<v>` — verify the header
  matches the source YAML versions in any PR that edits the YAML
- **Active-plan / scratchpad guards**: `active-plan-marker.sh` (uses
  `set -e` for strict marker semantics), `active-plan-lib.sh`
  (sourced library)

### Library files (`*-lib.sh`)

These are sourced by other scripts and intentionally omit their own
`set` flags (caller's settings apply). Currently shipped:

- `workspace-root-lib.sh` — `read_hook_input`, `resolve_workspace_root`
- `timeout-lib.sh` — `run_with_timeout`, `TIMEOUT_CMD` resolution
- `scratchpad-lib.sh` — scratchpad path/format helpers
- `active-plan-lib.sh` — active-plan marker helpers
- `ruby-dependency-lib.sh` — Ruby manifest detection helpers

Do NOT flag missing `set -o nounset` / `set -o pipefail` in these
files. Do flag a non-`-lib.sh` script that omits them.

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

## Cross-File Drift Around Hook Changes

- Any new/renamed `*.sh` under `hooks/scripts/` → check
  `hooks/hooks.json` references and any other script that sources it
  via `source "${BASH_SOURCE[0]%/*}/<lib>.sh"`
- Edit to `inject-iron-laws.sh` directly → reject; it is generated.
  Source change must go through `references/iron-laws.yml` /
  `preferences.yml` + `scripts/generate-iron-law-outputs.sh`
- New `RUBY_PLUGIN_*_TIMEOUT` env var → also document it in
  `.claude/rules/eval-workflow.md` env vars section if eval-relevant,
  and in this file under "Configurable Timeouts"
- New hook event registered in `hooks.json` → check Iron Law / preferences
  injection still fires; check at least one matching test in
  `lab/eval/tests/test_runtime_scripts.py`

## Do NOT Flag

- `exit 2` is intentional (feeds stderr to Claude, not an error)
- `jq -r '... // empty'` fallback patterns are intentional null-safety
- `HOOK_INPUT_VALUE` and `HOOK_NAME` variables from sourced libraries
- `workspace-root-lib.sh` sourcing pattern
- Long case statements in block-dangerous-ops.sh (necessary coverage)
- `run_with_timeout` / `timeout` / `gtimeout` wrapping external commands
- `TIMEOUT_CMD` resolution pattern (timeout → gtimeout → empty fallback)
- `RUBY_PLUGIN_*` env var defaults via `${VAR:-default}` syntax
- `*-lib.sh` files without their own `set -o nounset` / `set -o pipefail`
- `inject-iron-laws.sh` containing a single HEREDOC with no `set` flags
  (advisory injection, fail-open by design — see header comment)
- `active-plan-marker.sh` using `set -e` (strict marker semantics)
