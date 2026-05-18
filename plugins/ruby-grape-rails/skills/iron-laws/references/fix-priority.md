# Iron Law Fix Priority

## Priority Order

Iron Laws 1-20 are violation rules — every violation is a Blocker
(non-negotiable per
`plugins/ruby-grape-rails/skills/triage/references/triage-patterns.md`
§ "Always Fix"). Laws 21 and 22 are workflow gates, not severity
classifications.

1. **Blockers** (Laws 1-20): Every violation blocks merge. Single
   severity — no internal critical/warning split.
2. **Verification gate** (Law 21): Run the actual test/lint stack
   before claiming done. Failure here halts the workflow, not the
   merge.
3. **Surgical Changes gate** (Law 22): Every changed line must trace
   to the user's request. Out-of-scope edits are flagged but routed
   to `/rb:techdebt`, not blocked.

## Blocker Laws

| Law | Category | Why Blocker |
|-----|----------|-------------|
| 1 | Money as float | Financial data corruption |
| 2, 15 | SQL injection | Security vulnerability |
| 3 | N+1 queries | Performance / DB load |
| 4, 11 | after_commit for jobs | Data race conditions |
| 5 | Transaction boundaries | Partial-write data corruption |
| 6 | Validation bypass | Data integrity loss |
| 7 | default_scope | Unexpected query behavior |
| 8 | Idempotent jobs | Retry-safety; double-effect risk |
| 9 | JSON-safe Sidekiq args | Serialization failures |
| 10 | Objects in job args | Serialization failures |
| 12 | Eval with user input | Remote code execution |
| 13 | Missing authorization | Unauthorized access |
| 14 | Unsafe HTML | XSS attacks |
| 16 | method_missing without respond_to_missing? | Broken introspection |
| 17 | Supervise background processes | Production outage on crash |
| 18 | `rescue Exception` | Lost interrupts, hung processes |
| 19 | DB queries in Turbo Streams | Lock / deadlock under load |
| 20 | Missing `turbo_frame_tag` | Degraded UX, full page reloads |

## Additional Heuristics

Beyond the 22 laws, also watch for:

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
