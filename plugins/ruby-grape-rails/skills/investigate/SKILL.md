---
name: rb:investigate
description: "Root-cause analysis for Ruby/Rails/Grape bugs whose cause is unknown. Triggers: \"why is this broken\", \"root cause\", \"error analysis\". Do NOT use for: perf, tracing."
argument-hint: <bug description>
effort: high
---
# Investigate Ruby Bugs

Run a structured investigation instead of guessing.

## STEP 0: Read the investigation discipline references

Read `${CLAUDE_SKILL_DIR}/references/discipline.md` and
`${CLAUDE_SKILL_DIR}/references/error-patterns.md`. Apply the
verify-loop discipline + error-classification rubric as the
canonical procedure.

## Investigation Tracks

- request path and route trace
- data and transaction analysis
- background job / Redis analysis
- verification and reproduction loop

## Default Tools

- `bundle exec rspec path/to/spec.rb:LINE` or `bin/rails test`
- `bundle exec rails runner`
- `psql` for SQL inspection
- `redis-cli` for queue/cache inspection
- app logs and Sidekiq logs

## Output

Write a short investigation report with:

- observed behavior
- likely root cause
- confirming evidence
- safest next step (`/rb:plan` or `/rb:quick`)

## Agent Dispatch

This is a **skill** (`/rb:investigate`), not an agent. Do NOT spawn
`investigate` or `rb-investigate` via the Agent tool. For agent-based deep
investigation, use `deep-bug-investigator`
(`subagent_type: "ruby-grape-rails:deep-bug-investigator"`). When spawning,
pass an explicit output path in the prompt
(`.claude/investigations/deep-bug-investigator/{slug}-{datesuffix}.md`);
the agent writes its findings to that file and returns a ≤300-word chat
summary. Read the file for the full report.

If the agent's return text matches the pause signature in
`${CLAUDE_PLUGIN_ROOT}/references/agent-resume.md`, follow that protocol
to resume the agent before treating the artifact as missing.

## Gotchas

- Re-probing ruled-out hypotheses. Check `## Ruled Out` scratchpad
  section FIRST. Don't re-run grep / Read on file already eliminated.
- "Looks like X" without backtrace. Stack frame top-to-bottom is the
  only acceptable evidence for "the cause is in module X". Pattern
  matching against error message text is hypothesis, not evidence.
- Premature root-cause naming. State observed symptoms before
  hypothesizing cause. "Test fails on line 42 with NameError" is fact;
  "the bug is in Y constant" is hypothesis until reproduced.
- Skipping reproduction step. Always write a minimal failing spec
  before any code change. Cannot reproduce → no root cause.

## References

| Need | Reference |
|---|---|
| investigation discipline (no guessing, structured tracks) | `${CLAUDE_SKILL_DIR}/references/discipline.md` |
| investigation report template (Ralph Wiggum checklist + Root Cause + Fix) | `${CLAUDE_SKILL_DIR}/references/investigation-template.md` |
| common error-pattern catalog | `${CLAUDE_SKILL_DIR}/references/error-patterns.md` |
| quick debug commands + common-fix recipes (string vs atom keys, eager-load gaps, nil propagation) | `${CLAUDE_SKILL_DIR}/references/debug-commands.md` |
| production-incident triage flow (payload → reproduction → fix → verify → capture) | `${CLAUDE_SKILL_DIR}/references/incident-playbook.md` |

## Related — invoke manually if needed

<!-- BEGIN-GENERATED related-footer -->
- Slow / latency / memory regression → `/rb:perf` (performance analysis)
- Library or approach comparison → `/rb:research` (evidence-based research)
- Gem or Rails Guide lookup → `/rubydoc-fetcher` (cheap doc lookup)
- Request-state / session-leak hygiene check → `/rb:state-audit` (request-state hygiene)
- Live runtime introspection (Tidewave) → `/rb:runtime` (Tidewave runtime introspection)
- Adjacent debt noticed but out of scope → `/rb:techdebt` (tech-debt logging)
<!-- END-GENERATED related-footer -->
