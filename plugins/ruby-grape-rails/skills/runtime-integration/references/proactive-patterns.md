# Proactive Runtime Patterns

Push-like patterns using runtime tooling within MCP's pull constraints.
Instead of waiting for the developer to ask, these patterns
**automatically query runtime state at workflow checkpoints**.

## Philosophy

Agents should understand the relationship between code AND running behavior.
MCP is pull-only, but we simulate push by proactively querying
at the right moments.

**Shift from**: "Use runtime tooling tools when you need to" (reactive)
**Shift to**: "Always check runtime state at checkpoints" (proactive)

## When to Proactively Query

### During Work Phase (per-task runtime check)

After editing `.rb` files, call `mcp__tidewave__get_logs level: :error`
to catch runtime errors that static analysis misses (config issues,
module loading problems, database connection failures).

If errors found, investigate immediately -- don't wait for
`bundle exec rspec` to surface them.

### During Work Phase (per-feature smoke test)

After completing all tasks for a domain feature:

```ruby
# ActiveRecord feature: create -> fetch -> verify (rolled back)
mcp__tidewave__project_eval """
ActiveRecord::Base.transaction do
  user = User.create!(
    email: "smoke-test-#{SecureRandom.hex(4)}@example.com",
    password: "valid_password_123"
  )
  fetched = User.find(user.id)
  raise "Mismatch!" unless fetched.email == user.email
  raise ActiveRecord::Rollback, "smoke_test_passed"
end
# Returns with rollback = success
"""
```

```sql
-- Schema verification after migration
-- mcp__tidewave__execute_sql_query
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'target_table'
ORDER BY ordinal_position;
```

### During Planning Phase (context gathering)

Before spawning research agents:

```ruby
# Understand current data model
mcp__tidewave__project_eval """
User.column_names
"""

# Understand current routes
mcp__tidewave__project_eval """
Rails.application.routes.routes.map { |r| [r.verb, r.path.spec.to_s] }
"""

# Check for existing warnings in planned area
mcp__tidewave__get_logs level: :warning
```

Pass gathered context to research agent prompts so they
work with concrete project state, not assumptions.

### During Investigation (auto-capture)

When investigating a bug, auto-capture BEFORE asking the user:

```ruby
# Step 1: Capture recent errors
mcp__tidewave__get_logs level: :error

# Step 2: Correlate with source
mcp__tidewave__project_eval """
Rails.backtrace_cleaner.clean($!.backtrace) if $!
"""

# Step 3: Inspect live state
mcp__tidewave__project_eval """
# Check relevant model counts, associations, or query results
# relevant to the reported bug
User.count
"""
```

Present pre-populated investigation context rather than
asking the developer to copy-paste errors.

## Integration Points

| Workflow Phase | Checkpoint | runtime tooling Query | Purpose |
|---------------|------------|----------------|---------|
| Plan | Before agents | Schema introspection, routes eval | Concrete project context |
| Plan | Before agents | `get_logs :warning` | Existing issues in planned area |
| Work | Per-task | `get_logs :error` | Runtime error detection |
| Work | Per-feature | `project_eval` smoke test | Behavioral verification |
| Work | Per-feature | `execute_sql_query` | Schema/data verification |
| Investigate | Entry | `get_logs :error` | Auto-capture errors |
| Investigate | Hypothesis | `project_eval` | Test fix before applying |
| Review | Pre-review | `get_logs :error` | Catch runtime issues reviewers miss |

## Tidewave Requirement

These proactive patterns require Tidewave Rails:

```bash
bundle add tidewave --group development
```

If Tidewave is not available, use standard development workflows:

- Run tests with `bundle exec rspec`
- Check logs manually
- Use `rails console` for introspection
