---
name: rb:constraint-debug
description: Diagnose Active Record constraint failures, unique index violations, foreign-key errors, and migration/data mismatches.
argument-hint: "[error|path]"
effort: medium
paths:
  - app/models/**
  - db/**
  - "**/app/models/**"
  - "**/db/**"
---
# Constraint Debug

Check:

- the actual database constraint or index definition
- whether application validation matches database truth
- whether the failing write should be wrapped in a transaction or lock
- whether stale data or a bad migration introduced the mismatch
