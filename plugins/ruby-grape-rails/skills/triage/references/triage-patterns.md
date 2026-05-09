# Triage Patterns

## Common Triage Decisions

### Always Fix (auto-approve, don't even ask)

ALL Iron Law violations + security issues. Iron Laws are
non-negotiable per the review BLOCKER contract; do NOT downgrade them
to "Usually Fix":

- SQL injection / XSS via `.html_safe` or `raw()` with untrusted content (Iron Law 14)
- SQL string interpolation / concatenation (Iron Law 2 + 15)
- Ruby `eval` / `instance_eval` / `class_eval` with user input (Iron Law 12)
- Missing authorization in controller actions (Iron Law 13)
- `float` used for money fields (Iron Law 1)
- N+1 queries — missing `.includes()` / `.preload()` (Iron Law 3)
- `after_save` where `after_commit` is required (Iron Law 4)
- Multi-step operations without transaction wrap (Iron Law 5)
- `update_columns` / `save(validate: false)` in normal flows (Iron Law 6)
- `default_scope` on models (Iron Law 7)
- Non-idempotent Sidekiq jobs (Iron Law 8)
- Sidekiq args with symbols / non-JSON-safe types (Iron Law 9)
- ORM objects passed as Sidekiq args (Iron Law 10)
- `after_save` enqueueing instead of after-commit hook (Iron Law 11)
- `method_missing` without `respond_to_missing?` (Iron Law 16)
- Unsupervised background processes (Iron Law 17)
- Bare `rescue` / `rescue Exception` (Iron Law 18)
- DB queries inside Turbo Stream responses (Iron Law 19)
- Partial updates without `turbo_frame_tag` (Iron Law 20)
- "Should work" claims without test output (Iron Law 21)
- `bundle exec rails zeitwerk:check` failures
- Hard-coded credentials / API keys (cleartext secrets — security issue)

### Usually Fix

Non-Iron-Law, non-security issues worth addressing:

- Tests without assertions or using `sleep`
- Missing error handling on external API calls
- Missing rate limiting on user-facing endpoints
- Missing pagination on list endpoints over a small bound

### Often Skip

Low-impact or cosmetic issues:

- RuboCop style suggestions (unless enforced)
- Private class documentation
- Cosmetic naming improvements
- "Could use method chain" style suggestions
- Adding type hints to private methods

### Context-Dependent

Ask the user for these — the right answer depends on project
stage and priorities:

- Performance optimizations (premature vs. needed)
- Test coverage for edge cases (shipping deadline?)
- Refactoring suggestions (tech debt budget?)
- Documentation improvements (internal vs. public API?)

## Severity Reclassification Guide

### Pre-existing findings (do NOT downgrade)

Pre-existing findings (review's `New? = Pre-existing` column) keep
their bucket but are excluded from `## Summary`, `## Reviewer
Coverage`, and the consolidated verdict per
`plugins/ruby-grape-rails/skills/review/references/review-playbook.md`
§ "Pre-existing Issues". Triage routes them to the plan's
`## Pre-existing Issues (informational)` section only. NEVER
auto-include in any Phase. Do NOT relabel a pre-existing BLOCKER as
WARNING / SUGGESTION.

### Downgrade from BLOCKER (non-Iron-Law, non-security, NEW findings only) when

- The issue is in code that's not yet reachable
- There's an existing workaround in production
- The fix requires a separate migration/PR

Iron Law violations + security issues are both non-negotiable
BLOCKERs per the "Always Fix" list above. Do NOT downgrade EITHER
class on these grounds:

- Iron Laws (1-22): listed under "Always Fix"
- Security issues: hard-coded credentials / API keys, SQL injection,
  XSS, missing authorization, `eval` with user input, mass-assignment
  on protected fields, SSRF, secrets leakage

### Upgrade from SUGGESTION when

- The pattern will be copied by future developers
- It affects a security-sensitive code path
- It causes confusion in code review
- It violates an Iron Law

## Triage Anti-Patterns

### "Fix everything" without thinking

If you approve every finding, you didn't need triage. Either
skip triage and go straight to `/rb:plan`, or be more
selective about what's worth fixing now.

### "Skip everything" to ship faster

If you skip more than 70% of findings, the review wasn't
useful or you're cutting too many corners. At minimum, fix
all BLOCKERs and most WARNINGs.

### Triaging without reading

Each finding deserves 10-30 seconds of thought. If you're
pattern-matching on severity alone, you're missing context.

## Batch Triage for Large Reviews

When a review has 15+ findings:

1. First pass: Auto-approve all BLOCKERs
2. Second pass: Present WARNINGs for decision
3. Third pass: Batch SUGGESTIONs — "Skip all suggestions?"

This prevents decision fatigue on large reviews.
