---
name: rb:audit
description: "Use when you need a broad project-wide audit of a Ruby/Rails/Grape codebase covering architecture, security, performance, testing, and operational risk."
when_to_use: "Triggers: \"audit the project\", \"codebase health check\", \"architecture review\", \"security audit\", \"project-wide assessment\". Does NOT handle: reviewing individual PRs or diffs, fixing issues, running tests."
effort: xhigh
---
# Audit

Review five areas:

- boundaries and code ownership
- security and auth surfaces
- data integrity and query quality
- test depth and flake risk
- deploy/runtime readiness

## References

| Need | Reference |
|---|---|
| service-object health matrix, fan-in/out scoring, boundary violation checks | `${CLAUDE_SKILL_DIR}/references/architecture-checks.md` |
| A-F grade scoring per category + weighted overall score | `${CLAUDE_SKILL_DIR}/references/scoring-methodology.md` |
