---
name: active-record-patterns
description: "Active Record patterns: models, queries, associations, transactions, locking, migration design. Triggers: \"AR scope\", \"has_many through\", \"optimistic locking\", \"polymorphic\". Do NOT use for: Sequel, N+1 diagnosis."
user-invocable: false
effort: medium
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

## References

| Need | Reference |
|---|---|
| transactions, locking, partial-failure recovery | `${CLAUDE_SKILL_DIR}/references/transactions.md` |
| validation patterns, `update_columns` audit trails | `${CLAUDE_SKILL_DIR}/references/validations.md` |
| query composition, scopes, subqueries, batched inserts | `${CLAUDE_SKILL_DIR}/references/queries.md` |
| production-safe migration recipes | `${CLAUDE_SKILL_DIR}/references/migrations.md` |
| PostgreSQL full-text + trigram + hybrid search | `${CLAUDE_SKILL_DIR}/references/fulltext-search.md` |

## Related — invoke manually if needed

<!-- BEGIN-GENERATED related-footer -->
- Sequel ORM (non-Active Record) work → `/rb:sequel-patterns` (Sequel ORM patterns)
<!-- END-GENERATED related-footer -->
