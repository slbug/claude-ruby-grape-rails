---
name: active-record-patterns
description: "Use when working with Active Record models, migrations, queries, associations, transactions, locking, search, or data integrity patterns."
when_to_use: "Triggers: \"Active Record\", \"migration\", \"query\", \"association\", \"model\", \"database\", \"transaction\"."
user-invocable: false
effort: medium
paths:
  - "app/{models,repositories}/**"
  - "db/**"
  - "**/app/{models,repositories}/**"
  - "**/db/**"
  - "{packs,engines,components}/*/{models,repositories}/**"
  - "app/{packages,packs}/*/{models,repositories}/**"
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
