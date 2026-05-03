---
paths:
  - plugins/ruby-grape-rails/hooks/**
---

# Hook Development

## Audience: Agents, Not Humans

Hook scripts are code. Comments inside hook scripts (`.sh` / `.rb`
under `hooks/scripts/`) follow normal code-comment conventions —
this rule does NOT apply to executable hook source. Markdown
authored ABOUT hooks (skill refs explaining hook behavior) follows
the agent-readable rule: imperative, no narration, no `#` thinking
lines inside Bash blocks of skill docs (preference #6).

## Hook Failure Policy

- **Advisory hooks** (detect-runtime, check-resume, log-progress): warn or skip on degraded state, say so clearly
- **Delegated Ruby guardrails** (rubyish-post-edit, format-ruby, verify-ruby, debug-statement-warning): fail closed once selected for a Ruby-ish path
- **Security hooks** (secret-scan, block-dangerous-ops): fail closed in strict/high-confidence cases; document any narrower advisory fallback explicitly

Add or update a short policy comment near the top of the hook when behavior changes.

## Hook Output Patterns

- `PostToolUse` stdout is verbose-mode only — use `exit 2` + stderr to feed messages to Claude
- `PreCompact` has no context injection path — use user-facing stderr reminder only, rely on `PostCompact` to re-read artifacts
- `SessionStart` stdout IS added to Claude's context (exception along with `UserPromptSubmit`)
- `SubagentStart` uses `hookSpecificOutput.additionalContext` to inject context into subagents
- `PostToolUseFailure` uses `hookSpecificOutput.additionalContext` for debugging hints

## Deletion Safety Rule

- `rm -f` only for `mktemp` outputs or exact fixed plugin-owned paths
- `rm -rf` only for validated `mktemp -d` outputs
- `rmdir` for expected-empty lock directories
- For variable-based cleanup, validate the path/prefix first and use `${var:?}` in the final delete

## Hook Modes

- **default** (implicit): quieter startup, scan normal files, skip binary/media, avoid recent-change fallback
- **strict**: scan every written file, broaden secret scanning to recent changes
- Configure via `${REPO_ROOT}/.claude/ruby-plugin-hook-mode` or `RUBY_PLUGIN_HOOK_MODE=strict`

## Active Plan Infrastructure

`active-plan-lib.sh` / `active-plan-marker.sh` manage `.claude/ACTIVE_PLAN` marker file:

- **Set by:** `/rb:plan` after creating standalone plan, OR `/rb:full` before
  invoking `/rb:plan` to pre-bind the plan namespace
- **Cleared by:** `/rb:work` (when all tasks complete). `/rb:full` skill body
  tracks PLAN_DIR locally for its own progress.md State writes; later phases
  (`/rb:verify`, `/rb:review`, `/rb:compound`) do not require the marker —
  they resolve from current state / argument flags.
- **Read by:** session resume detection, `precompact-rules.sh`,
  `check-scratchpad.sh` (verified: calls `get_active_plan` at line 39),
  `log-progress.sh`, `postcompact-verify.sh`, `stop-failure-log.sh`,
  `/rb:plan` strict pre-bind detection (direct file read, not via
  `get_active_plan` fallbacks).
- `/rb:full` orchestrates the lifecycle via plan/work phases from the
  skill body in the main session.

Marker lifecycle is enforced at the skill level, not via hooks.
