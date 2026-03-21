---
name: rb:state-audit
description: Audit Rails request state, CurrentAttributes, Turbo stream flows, session usage, caching, and Redis-backed state for leaks, duplication, or confusion.
argument-hint: [path|feature]
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

```bash
# Find Current assignments in jobs and async code
grep -r "Current\." app/jobs/ app/workers/ --include="*.rb"

# Check for custom thread/fiber usage with Current
grep -r "Thread.new\|Concurrent\|Async" app/ --include="*.rb" -A 5 | grep -i current
```

**Verify:**

- [ ] Jobs using `Current` explicitly set context via `Current.set` or pass values as args
- [ ] Custom threads/fibers don't access `Current` without explicit context
- [ ] External collaborators (Time.zone, etc.) registered via `resets { ... }` if needed
- [ ] Not over-stuffing controller-specific values into global Current

See: [references/audit-procedures.md#currentattributes-usage](references/audit-procedures.md)

### Step 2: Session Bloat Detection

Detect session store type first:

```bash
# Check configured session store
grep -r "config.session_store" config/initializers/ config/application.rb
```

**For ActiveRecord session store:**

```bash
# In rails console
ActiveRecord::SessionStore::Session.pluck(:data).map { |d| d.to_s.bytesize }.max
```

**For Cookie-based sessions:**

```bash
# Check cookie size in browser dev tools or logs
# Look for CookieOverflow errors in logs
grep "CookieOverflow" log/production.log
```

**For Cache/Redis-backed sessions:**

```bash
# Check session key sizes
redis-cli --scan --pattern "*session*" | xargs -I {} redis-cli strlen {}
```

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

```bash
# Find Redis namespace in config
grep -r "redis\|Redis" config/initializers/ config/application.rb | grep -i namespace
```

```bash
# Find keys without TTL
redis-cli --scan | while read key; do
  ttl=$(redis-cli ttl "$key")
  if [ "$ttl" -lt 0 ]; then
    echo "$key (no TTL)"
  fi
done
```

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

```bash
# Find broadcast calls
grep -r "broadcast_" app/models/ --include="*.rb"

# Check for DB queries in turbo stream templates
grep -r "<%.*\.each\|<%.*\.where\|<%.*\.find" app/views/**/*.turbo_stream.*
```

**Verify:**

- [ ] All broadcasts in `after_commit` (not `after_save`)
- [ ] No DB queries in `.turbo_stream.*` templates
- [ ] Stream data pre-computed

See: [references/audit-procedures.md#turbo-stream-double-work](references/audit-procedures.md)

See also: [Hotwire State Analysis](references/hotwire-state-analysis.md) — Controller instance variables and stream data auditing

### Step 5: Source of Truth Validation

Search for denormalization patterns:

```bash
# Find counter updates
grep -r "update.*count\|update.*total" app/models/ --include="*.rb"

# Find manual cache invalidation
grep -r "Rails.cache.delete\|expire_fragment" app/ --include="*.rb"
```

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
