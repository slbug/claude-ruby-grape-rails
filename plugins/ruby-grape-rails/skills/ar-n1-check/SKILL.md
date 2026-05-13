---
name: rb:n1-check
description: "Diagnosing N+1 query patterns in Rails/Grape: slow index pages, serializers, nested API responses. Triggers: \"N+1\", \"includes\", \"preload\", \"bullet warning\"."
argument-hint: "[path|feature]"
effort: medium
---
# N+1 Check

Look for:

- loops that hit associations lazily
- serializers/presenters causing repeated loads
- controller or endpoint code that fetches parents and then children one-by-one
- missing preload strategy for nested responses
- places where `strict_loading` or Bullet-style checks would surface the problem earlier

## References

| Need | Reference |
|---|---|
| preload / includes / eager_load decision matrix | `${CLAUDE_SKILL_DIR}/references/preload-patterns.md` |
| broader query optimization (CTEs, window functions, batched inserts/updates) | `${CLAUDE_SKILL_DIR}/references/query-optimization.md` |
