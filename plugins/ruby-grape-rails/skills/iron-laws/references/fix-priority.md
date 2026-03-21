# Iron Law Fix Priority

## Priority Order

1. **Critical** (Laws 1, 2, 4, 6, 7, 10, 11, 12, 13, 14, 15): Security, data integrity, correctness — Fix immediately
2. **Warnings** (Laws 3, 5, 8, 9, 16, 17, 18, 19, 20): Performance, maintainability — Fix before merge
3. **Verification** (Law 21): Testing discipline — Required for completion

## Critical Laws

| Law | Category | Why Critical |
|-----|----------|--------------|
| 1 | Money as float | Financial data corruption |
| 2, 15 | SQL injection | Security vulnerability |
| 4, 11 | after_commit for jobs | Data race conditions |
| 6 | Validation bypass | Data integrity loss |
| 7 | default_scope | Unexpected query behavior |
| 10 | Objects in job args | Serialization failures |
| 12 | Eval with user input | Remote code execution |
| 13 | Missing authorization | Unauthorized access |
| 14 | Unsafe HTML | XSS attacks |

## Additional Heuristics

Beyond the 21 laws, also watch for:

- **Index foreign keys** — Performance (not a Law)
- **No secrets in logs** — Filter sensitive params
- **Thin controllers** — Delegate to service objects
- **Strong parameters** — Always whitelist
- **Explicit retry strategy** — Configure Sidekiq retry
- **Handle dead letter queue** — Don't lose failed jobs

## Valid Exceptions

Document exceptions with comments:

- `update_columns` for background migrations
- `raw()` for trusted admin templates
- `rescue Exception` in top-level error handlers
- `eval` in controlled DSL contexts
