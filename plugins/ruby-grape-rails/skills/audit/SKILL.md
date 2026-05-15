---
name: rb:audit
description: "Running a project-wide audit of a Ruby/Rails/Grape codebase: architecture, security, performance, testing coverage, ops risk. Emits findings to .claude/audit/."
effort: xhigh
disable-model-invocation: true
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

## Related — invoke manually if needed

<!-- BEGIN-GENERATED related-footer -->
- Slow / latency / memory regression → `/rb:perf` (performance analysis)
- Compression telemetry summary → `/rb:compression-report` (internal QA (telemetry report))
- Research trust / source-quality audit → `/rb:provenance-scan` (research-trust audit)
- Service-boundary or split-monolith decision → `/rb:boundaries` (service-boundary analysis)
- Request-state / session-leak hygiene check → `/rb:state-audit` (request-state hygiene)
- Adjacent debt noticed but out of scope → `/rb:techdebt` (tech-debt logging)
- Skill-router telemetry summary → `/rb:discovery-report` (internal eval-tuning tool — drafts a redacted report from skill-discovery telemetry)
<!-- END-GENERATED related-footer -->
