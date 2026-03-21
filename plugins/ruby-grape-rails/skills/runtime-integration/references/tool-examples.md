# runtime tooling Tool Examples

## project_eval - Execute Ruby Code

Best for: Testing functions, inspecting state, quick experiments

```ruby
# Test a model method
User.find(1)

# Check application config
Rails.application.config.active_record.query_cache

# Test validation
user = User.new(email: "test@example.com")
user.valid?
user.errors.full_messages

# Check module loaded
defined?(MyApp::SomeModule)

# Reload in development (if needed)
reload!
```

## execute_sql_query - Database Operations

Best for: Verifying data, checking migrations, debugging queries

```sql
-- Check table structure
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'users';

-- Verify migration ran
SELECT * FROM schema_migrations ORDER BY version DESC LIMIT 5;

-- Check indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'users';

-- Debug query results
SELECT u.*, COUNT(p.id) as post_count
FROM users u
LEFT JOIN posts p ON p.user_id = u.id
GROUP BY u.id;

-- Check Sidekiq jobs
SELECT id, class, args, status, scheduled_at
FROM sidekiq_jobs  -- if using Sidekiq Pro or similar
ORDER BY created_at DESC
LIMIT 10;

-- Table exists?
SELECT EXISTS (
  SELECT FROM information_schema.tables
  WHERE table_name = 'users'
);
```

## get_docs - Fetch Documentation

Best for: Looking up method signatures, class docs, exact API

```
# Class documentation
ActiveRecord::Base

# Specific method
ActiveRecord::FinderMethods#find

# Query methods
ActiveRecord::QueryMethods#where

# Association methods
ActiveRecord::Associations::ClassMethods#has_many
```

**Advantage**: Returns docs for exact versions in your Gemfile.lock

## get_source_location - Find Code

Best for: Locating classes/modules, finding implementations

```ruby
# Find class location
User.instance_method(:save).source_location

# Find method
User.method(:create).source_location

# Check if method defined
User.method_defined?(:some_method)
```

Returns: `["app/models/user.rb", 42]` (file path and line number)

## Introspect Data Model

Best for: Understanding existing models, checking fields/associations

```ruby
# All model attributes
User.attribute_names

# Column details
User.columns_hash

# Associations
User.reflect_on_all_associations.map { |a| [a.name, a.macro, a.class_name] }

# Validations
User.validators.map { |v| [v.attributes, v.class] }
```

## get_logs - Application Logs

Best for: Debugging errors, tracing requests

```ruby
# Filter by level
Rails.logger.error "Error message"
Rails.logger.warn "Warning message"

# Read from log file (if accessible)
tail -f log/development.log | grep ERROR
```

## Workflow Integration

### When Planning Features

1. Understand existing patterns: `User.column_names`, `User.reflect_on_all_associations`
2. Check documentation: `get_docs` for relevant modules
3. Find similar code: `get_source_location`

### When Implementing

1. Test as you go: `project_eval` after each method
2. Verify queries: `execute_sql_query` for ActiveRecord queries
3. Check for errors: `get_logs level: :error`

### When Debugging

1. Find the code: `get_source_location`
2. Read logs: `get_logs`
3. Test fix: `project_eval`
4. Verify data: `execute_sql_query`

### When Investigating Memory Leaks

Use `project_eval` to walk through a structured investigation:

```ruby
# 1. Check Ruby object count
ObjectSpace.count_objects

# 2. Find largest strings
ObjectSpace.each_object(String).max_by(10) { |s| s.bytesize }

# 3. Check ActiveRecord cache
ActiveRecord::Base.connection.query_cache.size

# 4. Check loaded classes
ObjectSpace.each_object(Class).count
```

Flow: enumerate objects → find outliers → check memory usage → trace sources → propose fix
