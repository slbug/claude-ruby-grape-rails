# Iron Law Fix Priority

## Priority Order

Every Iron Law violation (Laws 1-22) is a Blocker — non-negotiable
per `plugins/ruby-grape-rails/skills/triage/references/triage-patterns.md`
§ "Always Fix". The three groups below differ by what the violation
checks, not by severity.

1. **Violation rules** (Laws 1-20): Code patterns that introduce
   bugs, security holes, or data corruption. Block merge directly.
2. **Verification discipline** (Law 21): Run actual tests/lint and
   show results before claiming done. Violation = "should work"
   claim without evidence. Failed tests/lint that come from running
   them are themselves separate Blockers — surface them, do not
   merge.
3. **Surgical-change discipline** (Law 22): Every changed line must
   trace to the user's request. Violation = unrelated edits in the
   diff. Block merge until out-of-scope edits are reverted or split
   into a separate change.

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
| 18 | `rescue Exception`, `rescue ::Exception`, `rescue_from(Exception)`, `rescue_from ::Exception` | Lost interrupts, hung processes |
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
- `eval` in controlled DSL contexts

`rescue Exception` and `rescue ::Exception` — in either `begin/rescue`
or Rails `rescue_from` — have NO valid exemption per current Law 18.
Top-level handlers must rescue specific subclasses or use
`SignalException`/`SystemExit` handlers from the language explicitly.
