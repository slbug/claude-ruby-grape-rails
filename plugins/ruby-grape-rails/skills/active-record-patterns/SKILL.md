---
name: active-record-patterns
description: Active Record patterns for querying, associations, migrations, transactions, locking, search, and data integrity. Load for any model, migration, query, or database-heavy work.
user-invocable: false
effort: medium
paths:
  - app/models/**
  - db/**
  - "**/app/models/**"
  - "**/db/**"
---
# Active Record Patterns

## Iron Laws

1. Use `decimal` or integer cents for money.
2. Prevent N+1 queries with intentional preload strategy.
3. Put invariants inside transactions and use locks when races matter.
4. Prefer `after_commit` for external side effects.
5. Keep schema constraints aligned with application validations.

## Default Moves

- use foreign keys and indexes deliberately
- choose `includes`, `preload`, or `eager_load` intentionally
- use `find_each` for large backfills and batch work
- use optimistic or pessimistic locking where correctness depends on it
- make migrations reversible and production-safe
