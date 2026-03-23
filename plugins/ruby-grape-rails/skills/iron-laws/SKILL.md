---
name: iron-laws
description: The 21 Iron Laws of Ruby/Rails/Grape development. Non-negotiable rules that prevent common, costly mistakes. Auto-loaded for Iron Law Judge.
effort: medium
---
# Iron Laws

## Overview

These 21 rules are NEVER violated. If code would violate them, STOP and explain before proceeding.

### Active Record (7 laws)

1. **Decimal for Money** — NEVER use float for money — use decimal or integer (cents)
2. **Parameterized Queries** — ALWAYS use parameterized queries — never interpolate user input into SQL strings
3. **Eager Loading** — USE includes/preload for associations — avoids N+1 queries
4. **Commit-Safe Enqueueing in Active Record** — IN Active Record code, use after_commit not after_save when enqueueing jobs
5. **Transaction Boundaries** — WRAP multi-step operations in transactions — use ActiveRecord::Base.transaction
6. **No Validation Bypass** — NO update_columns, update_column, or save(validate: false) in normal flows
7. **No default_scope** — NO default_scope — use explicit named scopes only

### Sidekiq (4 laws)

8. **Idempotent Jobs** — Jobs MUST be idempotent — safe to retry
9. **JSON-Safe Arguments** — Args use JSON-safe types only — no symbols, no Ruby objects, no procs
10. **No ORM Objects in Args** — NEVER store ORM objects in args — store IDs, not records
11. **Commit-Safe Enqueueing** — ALWAYS enqueue jobs after commit using the active ORM or transaction hook

### Security (4 laws)

12. **No Eval** — NO eval with user input — code injection vulnerability
13. **Explicit Authorization** — AUTHORIZE in EVERY controller action — do not trust before_action alone
14. **No Unsafe HTML** — NEVER use html_safe or raw with untrusted content — XSS vulnerability
15. **No SQL Concatenation** — NO SQL string concatenation — always use parameterized queries

### Ruby (3 laws)

16. **method_missing Requires respond_to_missing?** — NO method_missing without respond_to_missing? — breaks introspection
17. **Supervise Background Processes** — SUPERVISE ALL BACKGROUND PROCESSES — use proper process managers in production
18. **Rescue StandardError** — DON'T RESCUE Exception — only rescue StandardError or specific classes

### Hotwire/Turbo (2 laws)

19. **No DB Queries in Turbo Streams** — NEVER query DB in Turbo Stream responses — pre-compute everything before broadcast
20. **Use turbo_frame_tag** — ALWAYS use turbo_frame_tag for partial updates — prevents full page reloads

### Verification (1 law)

21. **Verify Before Claiming Done** — VERIFY BEFORE CLAIMING DONE — never say 'should work' or 'this fixes it.' Run bundle exec rspec or bin/rails test and show the result

## Response Format

When detecting a violation:

```
STOP: This code would violate Iron Law [number]: [description]

What you wrote:
[problematic code]

Correct pattern:
[fixed code]

Should I apply this fix?
```

## References

- `references/violation-patterns.md` — Detailed detection patterns and grep commands
- `references/fix-priority.md` — Critical vs warning violations and fix order
