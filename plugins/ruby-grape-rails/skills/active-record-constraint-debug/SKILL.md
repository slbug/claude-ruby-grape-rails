---
name: rb:constraint-debug
description: "Diagnosing Active Record constraint failures: unique-index, foreign-key, NOT-NULL violations. Triggers: \"constraint error\", \"unique violation\", \"foreign key\", \"PG::UniqueViolation\"."
argument-hint: "[error|path]"
effort: medium
---
# Constraint Debug

Check:

- the actual database constraint or index definition
- whether application validation matches database truth
- whether the failing write should be wrapped in a transaction or lock
- whether stale data or a bad migration introduced the mismatch

## References

| Need | Reference |
|---|---|
| race-condition upserts, FK violations, check-constraint debugging recipes | `${CLAUDE_SKILL_DIR}/references/constraint-patterns.md` |
