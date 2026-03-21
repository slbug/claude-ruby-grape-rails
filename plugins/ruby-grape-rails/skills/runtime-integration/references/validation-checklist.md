# Runtime Validation Checklist

Validate implementations using Tidewave Rails MCP tools.

## Prerequisites

Tidewave Rails must be installed:

```bash
bundle add tidewave --group development
```

## Schema & Migration

```ruby
# Verify schema loaded
mcp__tidewave__project_eval """
User.column_names
"""

# Check migration applied
mcp__tidewave__execute_sql_query """
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users'
ORDER BY ordinal_position
"""

# Verify indexes
mcp__tidewave__execute_sql_query """
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'users'
"""

# Test validation
mcp__tidewave__project_eval """
user = User.new(email: "test@example.com")
user.valid?
user.errors.full_messages
"""
```

## Context Functions / Service Objects

```ruby
# Test create
mcp__tidewave__project_eval """
UserRegistration.call(
  email: "test-#{SecureRandom.hex(4)}@example.com",
  password: "password123456"
)
"""

# Verify in DB
mcp__tidewave__execute_sql_query """
SELECT id, email, created_at FROM users ORDER BY created_at DESC LIMIT 5
"""
```

## Controllers / Views

```ruby
# Find controller
mcp__tidewave__project_eval """
UsersController.instance_method(:index).source_location
"""

# Check errors
mcp__tidewave__project_eval """
Rails.logger.error "Test error"
"""

# Verify assigns (in test or console)
mcp__tidewave__project_eval """
# In a controller spec or console
controller.instance_variable_get(:@users)
"""
```

## Sidekiq Jobs

```ruby
# Check enqueued
mcp__tidewave__project_eval """
Sidekiq::Queue.all.map { |q| [q.name, q.size] }
"""

# Test worker directly
mcp__tidewave__project_eval """
WelcomeEmailWorker.new.perform(user_id: 1)
"""

# Check failures
mcp__tidewave__project_eval """
Sidekiq::DeadSet.new.size
"""
```

## Quick Validation Template

```markdown
## Validation: [Feature Name]

### Schema/Data
- [ ] Migration applied
- [ ] Schema fields correct
- [ ] Indexes created
- [ ] Model validates

### Context Functions
- [ ] create_* works
- [ ] get_* works
- [ ] list_* works
- [ ] update_* works

### Web Layer
- [ ] Routes configured
- [ ] Controller responds
- [ ] Views render

### Tests
- [ ] Unit tests pass
- [ ] No regressions

### Logs
- [ ] No errors
- [ ] No warnings
```

## Troubleshooting

### Model Not Found

```ruby
# Check if class is defined
defined?(SomeModel)

# Check load path
$LOAD_PATH.grep(/models/)

# Reload
reload!
```

### Table/Column Not Found

```sql
-- Check table exists
SELECT EXISTS (
  SELECT FROM information_schema.tables
  WHERE table_name = 'users'
);

-- Check column exists
SELECT EXISTS (
  SELECT FROM information_schema.columns
  WHERE table_name = 'users' AND column_name = 'email'
);
```

### Sidekiq Issues

```ruby
# Check Redis connection
Sidekiq.redis { |r| r.ping }

# Check queues
Sidekiq::Queue.all.map(&:name)

# Check workers
Sidekiq::WorkSet.new.size
```
