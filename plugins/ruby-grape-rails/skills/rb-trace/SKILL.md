---
name: rb:trace
description: "Use when you need to trace a request, API call, background job, or service flow through Rails, Grape, and Sidekiq code to understand where a value changes or where a side effect comes from."
when_to_use: "Triggers: \"trace this request\", \"follow the code path\", \"where does this value change\", \"trace the flow\", \"how does this call propagate\". Does NOT handle: bug diagnosis with unknown cause, performance analysis."
argument-hint: <entry point>
effort: medium
---
# Trace Execution

Follow the path from the entry point through:

- routes and mounted Grape APIs
- controllers/endpoints
- service or command objects
- models and queries
- jobs, broadcasts, and cache writes

Write the trace as a short step-by-step chain with file paths.

## Agent Dispatch

This is a **skill** (`/rb:trace`), not an agent. Do NOT spawn `rb-trace` or
`rb:trace` via the Agent tool. For agent-based deep tracing, use `call-tracer`
(`subagent_type: "ruby-grape-rails:call-tracer"`).

## References

| Need | Reference |
|---|---|
| where tracing begins (controllers, Grape endpoints, jobs, rake, webhooks, middleware) | `${CLAUDE_SKILL_DIR}/references/entry-points.md` |
| extracting argument patterns from call sites | `${CLAUDE_SKILL_DIR}/references/argument-extraction.md` |
| Prism, TracePoint, RuboCop AST, Steep, Pronto | `${CLAUDE_SKILL_DIR}/references/static-analysis-tools.md` |
| production-incident triage flow (when trace is for a live failure) | `${CLAUDE_PLUGIN_ROOT}/skills/investigate/references/incident-playbook.md` |
