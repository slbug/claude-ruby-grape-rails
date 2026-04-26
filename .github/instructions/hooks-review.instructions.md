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
- PostToolUseFailure uses `hookSpecificOutput.additionalContext`
- PreCompact uses stderr for context reminders; exit 2 blocks compaction
  during active work/full phases

## Hook Failure Policy

Each script under `plugins/ruby-grape-rails/hooks/scripts/` must
document its failure policy near the top via a `# Policy:` comment.
Recognised classes:

- **Advisory** — warn/skip, exit 0 on degraded state. Default.
- **Delegated Ruby guardrail** — fail closed (exit 2) once selected
  for a Ruby path (e.g. `format-ruby.sh`, `verify-ruby.sh`).
- **Security-sensitive** — fail closed in strict/high-confidence
  cases (e.g. `secret-scan.sh`, `block-dangerous-ops.sh`,
  `iron-law-verifier.sh`).
- **Generated injector** — `inject-rules.sh` is rebuilt from
  `references/iron-laws.yml` + `preferences.yml` by
  `scripts/generate-iron-law-outputs.sh`. Do NOT hand-edit. The script
  is wired in `hooks.json` under both `SessionStart` (main session)
  and `SubagentStart` (per-subagent) and reads `hook_event_name`
  from the input to echo the matching value back in
  `hookSpecificOutput.hookEventName`. Header carries
  `Source versions: iron-laws=<v> preferences=<v>` — verify the
  header matches the source YAML versions in any PR that edits the YAML.
- **Active-plan / scratchpad guard** — `active-plan-marker.sh` uses
  `set -e` for strict marker semantics; `active-plan-lib.sh` is the
  sourced library.

When reviewing a hook, read the `# Policy:` comment to determine which
class applies, then use the matching set/exit/timeout expectations from
"Shell Hardening" + "Configurable Timeouts". Do not assume a class from
the filename alone.

### Library files (`*-lib.sh`)

Files matching `*-lib.sh` are sourced by other scripts and
intentionally omit their own `set` flags (caller's settings apply).
Do NOT flag missing `set -o nounset` / `set -o pipefail` in
`*-lib.sh`. Do flag a non-`-lib.sh` script that omits them.

## Configurable Timeouts

Hook scripts wrap slow sub-commands with `timeout` and env var overrides:

- `RUBY_PLUGIN_FORMATTER_TIMEOUT` (default 120s) — format-ruby.sh
- `RUBY_PLUGIN_RUBY_CHECK_TIMEOUT` (default 30s) — verify-ruby.sh
- `RUBY_PLUGIN_BETTERLEAKS_TIMEOUT` (default 60s) — secret-scan.sh
- `RUBY_PLUGIN_DETECT_STACK_TIMEOUT` (default 15s) — detect-runtime.sh

## Opt-out / Opt-in Env Vars

Some hooks honor an env var to gate behavior end-users want to control
without editing `settings.json`. Two shapes:

- **Opt-out** (`*_DISABLE_*`): hook does work by default; env=1 short-
  circuits to silent exit.
- **Opt-in** (`*_TELEMETRY=1`, `*_STRICT_*=1`): hook is dormant by
  default; env=1 turns on broader behavior.

Both forms must short-circuit BEFORE side effects, so toggling has
zero residue on the user's data dir, transcript, or context.

- `RUBY_PLUGIN_DISABLE_RULES_INJECTION=1` — `inject-rules.sh`. Skips
  Iron Laws + Advisory Preferences injection on `SessionStart` and
  `SubagentStart`. Useful when the plugin is installed at user scope
  but the active project is not Ruby/Rails/Grape. Short-circuits at
  the top of the script before reading stdin or sourcing
  `workspace-root-lib.sh`.
- `RUBY_PLUGIN_STRICT_PERMS=1` — `block-dangerous-ops.sh`. Adds
  `decision.interrupt: true` to the structured `PermissionRequest`
  deny, stopping Claude rather than just denying the single command.
  Pre-existing exit-2 hard-block on `PreToolUse` unchanged.
- `RUBY_PLUGIN_COMPRESSION_TELEMETRY=1` — `compress-verify-output.rb`.
  When unset (default), the verify-output compression collector is a
  no-op. When set, the hook appends to
  `${CLAUDE_PLUGIN_DATA}/compression.jsonl` and preserves the
  captured Bash output under
  `${CLAUDE_PLUGIN_DATA}/verify-raw/<uuid>.log`. Registered on BOTH
  `PostToolUse:Bash` and `PostToolUseFailure:Bash` so verify
  failures (rspec failures, brakeman findings, rubocop offenses)
  are captured alongside successful runs. Reads
  `tool_response.stdout`+`stderr` on `PostToolUse` and the top-level
  `error` field on `PostToolUseFailure`. Skips on user-interrupt.
  The plugin ships no command that deletes this telemetry: cleanup
  is the user's manual action. `compression-data-status.sh` is the
  matched `SessionStart` advisory hook — read-only, prints an
  `rm`-ready nudge when telemetry on disk crosses
  `references/compression/rules.yml` `advisory.size_threshold_bytes`
  or `advisory.sample_threshold`.

When reviewing changes that introduce a new opt-in env var, also
update this list and ensure the hook's `# Policy:` header documents
the opt-in default-off behavior explicitly.

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
- Edit to `inject-rules.sh` directly → reject; it is generated.
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
- `inject-rules.sh` reading `hook_event_name` and echoing it back in
  `hookSpecificOutput.hookEventName`. Same body, two registrations
  (advisory injection, fail-open by design — see header comment)
- `active-plan-marker.sh` using `set -e` (strict marker semantics)
