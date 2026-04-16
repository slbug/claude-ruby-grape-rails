---
name: rb:constraint-debug
description: "Use when diagnosing Active Record constraint failures, unique index violations, foreign-key errors, and migration/data mismatches."
when_to_use: "Triggers: \"constraint error\", \"unique violation\", \"foreign key\", \"PG::UniqueViolation\", \"migration failed\"."
argument-hint: "[error|path]"
effort: medium
paths:
  - "app/models/**"
  - "db/**"
  - "**/app/models/**"
  - "**/db/**"
  - "{packs,engines,components}/*/models/**"
  - "app/{packages,packs}/*/models/**"
---
# Constraint Debug

Check:

- the actual database constraint or index definition
- whether application validation matches database truth
- whether the failing write should be wrapped in a transaction or lock
- whether stale data or a bad migration introduced the mismatch
