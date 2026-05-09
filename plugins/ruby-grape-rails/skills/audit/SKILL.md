---
name: rb:audit
description: "Use when running project-wide audit: architecture, security, perf, testing, ops risk."
when_to_use: "Triggers: audit project, codebase health, architecture review, security audit."
effort: xhigh
---
# Audit

Review five areas:

- boundaries and code ownership
- security and auth surfaces
- data integrity and query quality
- test depth and flake risk
- deploy/runtime readiness

## Gotchas

- Scope creep. Audit reports stay project-wide; do NOT propose fixes
  mid-audit. `/rb:audit` is read-only — fixes route through `/rb:plan`.
- False-precision metrics. "23.5% of skills underperform" without
  sample size or corroboration is meaningless. Source every metric or
  downgrade language to advisory.
- Unverified third-party claims. "Library X handles Y safely" — verify
  against current docs (Context7 MCP) or Brakeman scan, never against
  training-data assumption.
- Schema drift. Iron Laws / preferences references must match current
  generator output. Regen via
  `bash scripts/generate-iron-law-outputs.sh all` if mismatched.

## References

| Need | Reference |
|---|---|
| service-object health matrix, fan-in/out scoring, boundary violation checks | `${CLAUDE_SKILL_DIR}/references/architecture-checks.md` |
| A-F grade scoring per category + weighted overall score | `${CLAUDE_SKILL_DIR}/references/scoring-methodology.md` |
