---
name: rb:state-audit
description: "Use when auditing Rails request state, CurrentAttributes, Turbo stream flows, session usage, caching, and Redis-backed state for leaks, duplication, or confusion."
when_to_use: "Triggers: \"request state\", \"CurrentAttributes\", \"session leak\", \"Redis state\", \"caching bug\"."
argument-hint: "[path|feature]"
effort: medium
---
# Request State Audit

Audit your Rails application for common state management issues that cause production bugs.

## What This Audit Covers

| Category | Issues Detected |
|----------|----------------|
| **CurrentAttributes** | Leakage across requests, missing resets, async flow contamination |
| **Session/Cookie** | Bloat, ActiveRecord objects stored, unbounded growth |
| **Redis** | Missing namespaces, keys without TTL, memory leaks |
| **Turbo Streams** | Double-work, broadcasts before commit, DB queries in streams |
| **Data Integrity** | Duplicated sources of truth, cache invalidation bugs |

## When to Run

- Before major releases
- When adding new `Current` attributes
- After switching to Turbo Streams
- When Redis memory usage grows unexpectedly
- After session-related bug reports

## Audit Procedure

### Step 1: CurrentAttributes Check

**Modern Rails Behavior:** CurrentAttributes automatically resets before and after each request. Manual reset middleware is not required for normal request flow.

**Audit Focus:** Jobs, threads, and async contexts where automatic reset does not apply.

Search for patterns:

- Use Grep: pattern `Current\.`, path `app/jobs` and `app/workers`, glob `*.rb`
- Use Grep: pattern `Thread\.new|Concurrent|Async|Fiber\.schedule`, path `app/`,
  glob `*.rb`, context 5 — then check results for `current` references

**Verify:**

- [ ] Jobs using `Current` explicitly set context via `Current.set` or pass values as args
- [ ] Custom threads/fibers don't access `Current` without explicit context
- [ ] External collaborators (Time.zone, etc.) registered via `resets { ... }` if needed
- [ ] Not over-stuffing controller-specific values into global Current

See: [references/audit-procedures.md#currentattributes-usage](references/audit-procedures.md)

### Step 2: Session Bloat Detection

Detect session store type first:

Use Grep: pattern `config\.session_store`, path `config/initializers` and `config/application.rb`.

**For ActiveRecord session store:** In rails console, run `ActiveRecord::SessionStore::Session.pluck(:data).map { |d| d.to_s.bytesize }.max`.

**For Cookie-based sessions:** Use Grep: pattern `CookieOverflow`, path `log/production.log`.

**For Cache/Redis-backed sessions:** Run `redis-cli --scan --pattern "*session*" | xargs -I {} redis-cli strlen {}` to measure session key sizes.

**Thresholds:**

- **Warning:** > 2KB
- **Critical:** > 4KB (cookie storage limit)

**Check:**

- [ ] No ActiveRecord objects stored
- [ ] Large collections not in session
- [ ] Flash messages properly cleared

See: [references/audit-procedures.md#sessioncookie-bloat](references/audit-procedures.md)

### Step 3: Redis Namespace & TTL Audit

Check your application's actual Redis namespace configuration:

Use Grep: pattern `redis.*namespace|namespace.*redis`, path `config/initializers` and `config/application.rb`, case-insensitive.

To find keys without TTL, run `redis-cli --scan | while read key; do ttl=$(redis-cli ttl "$key"); [ "$ttl" -lt 0 ] && echo "$key (no TTL)"; done`.

**Common namespace patterns** (check which your app uses):

- `#{Rails.env}:` (environment prefix)
- Application-specific prefix from config
- No prefix (check this doesn't cause collisions)

**Verify:**

- [ ] Keys follow your app's configured namespace pattern
- [ ] Cache writes have `expires_in`
- [ ] Session keys have expiration

See: [references/audit-procedures.md#redis-key-namespace--ttl](references/audit-procedures.md)

### Step 4: Turbo Stream Safety

- Use Grep: pattern `broadcast_`, path `app/models`, glob `*.rb`
- Use Grep: pattern `<%.*\.(each|where|find)`, path `app/views`, glob `*.turbo_stream.*`

**Verify:**

- [ ] All broadcasts in `after_commit` (not `after_save`)
- [ ] No DB queries in `.turbo_stream.*` templates
- [ ] Stream data pre-computed

See: [references/audit-procedures.md#turbo-stream-double-work](references/audit-procedures.md)

See also: [Hotwire State Analysis](references/hotwire-state-analysis.md) — Controller instance variables and stream data auditing

### Step 5: Source of Truth Validation

Search for denormalization patterns:

- Use Grep: pattern `update.*(count|total)`, path `app/models`, glob `*.rb`
- Use Grep: pattern `Rails\.cache\.delete|expire_fragment`, path `app/`, glob `*.rb`

**Verify:**

- [ ] Counters have clear invalidation strategy
- [ ] No scattered cache invalidation
- [ ] Materialized views properly refreshed

See: [references/audit-procedures.md#duplicated-sources-of-truth](references/audit-procedures.md)

## Output Format

Present findings by severity:

```
## Request State Audit Results

### Critical (Fix Immediately)
- Current.user accessed in job without context (app/jobs/order_job.rb:15)
  - Jobs don't inherit request context; use explicit args or Current.set
  - Fix: Pass user_id as arg, or wrap in Current.set(user: user) { ... }

### High Risk
- Session size 6.2KB (app/controllers/cart_controller.rb:45)
  - Storing full cart items in session
  - Fix: Store cart_id only, load from DB

### Warnings
- Redis keys without TTL: 1,247 found
  - Run: redis-cli --scan | xargs -L1 redis-cli expire 86400

### Recommendations
- Add Redis memory monitoring
- Implement session cleanup rake task
```

## References

- [Detailed Audit Procedures](references/audit-procedures.md) — Step-by-step checks with code examples
- [Remediation Patterns](references/audit-procedures.md#remediation-patterns) — Ready-to-use fixes
- [Investigation Tools](references/audit-procedures.md#tools-for-investigation) — Commands and debugging snippets
- [Hotwire State Analysis](references/hotwire-state-analysis.md) — Controller instance variables and stream data auditing
