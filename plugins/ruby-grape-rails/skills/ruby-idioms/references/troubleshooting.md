# Rails Troubleshooting Playbook

Production debugging for Rails applications. For code bugs, see `deep-bug-investigator` agent.

## Quick Diagnosis

| Symptom | Likely Cause | Section |
|---------|--------------|---------|
| High memory, growing | Memory leak, large ActiveRecord cache | Memory Issues |
| Slow responses | N+1 queries, slow database queries | Performance |
| Random crashes | Unhandled exceptions, job failures | Crashes |
| Timeouts | DB pool, slow external calls | Timeouts |
| Server unresponsive | Background jobs, slow queries | Rails Issues |

## Memory Issues

### Using Rails Console

```ruby
# In rails console - check memory usage
puts `ps -o rss= -p #{Process.pid}`.to_i / 1024  # Memory in MB

# Check ActiveRecord query cache
ActiveRecord::Base.connection.query_cache.size

# Clear query cache
ActiveRecord::Base.connection.clear_query_cache
```

### Common Causes

1. **ActiveRecord cache** - Use `uncached` for long operations
2. **Large result sets** - Use `find_each` for batch processing
3. **String retention** - Check for memoization without limits
4. **Background job memory** - Jobs may not release memory properly

## Performance Issues

### N+1 Query Detection

```ruby
# config/environments/development.rb - enable query logging
config.active_record.verbose_query_logs = true

# Use Bullet gem in development
gem 'bullet', group: :development

# In console - check for N+1
ActiveSupport::Notifications.subscribe('sql.active_record') do |*args|
  event = ActiveSupport::Notifications::Event.new(*args)
  puts "SQL: #{event.payload[:sql]}" if event.duration > 100
end
```

### Slow ActiveRecord Queries

```sql
-- Check pg_stat_statements (if enabled)
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10

-- Missing indexes
SELECT relname, seq_scan, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
ORDER BY seq_scan DESC
```

### Background Job Bottlenecks

```ruby
# Check Sidekiq queue depth
Sidekiq::Queue.all.map { |q| [q.name, q.size] }

# Check job latency
Sidekiq::Queue.new.latency  # seconds oldest job has been waiting
```

## Crashes

### Common Crash Patterns

| Error | Cause | Fix |
|-------|-------|-----|
| `ActiveRecord::ConnectionTimeoutError` | DB pool exhausted | Increase pool size or reduce query time |
| `ActiveRecord::Deadlocked` | Database deadlock | Retry with exponential backoff |
| `NoMethodError` | Nil access | Add nil-safety or validation |
| `ArgumentError` | Wrong argument type | Validate input before use |

### Checking Application Health

```ruby
# Check if database is accessible
ActiveRecord::Base.connection.execute("SELECT 1")

# Check Redis (if used)
Redis.current.ping

# Check background jobs
Sidekiq::ProcessSet.new.size  # Number of active workers
```

## Timeouts

### Database Pool Exhaustion

**Symptoms:** Random timeouts, "could not obtain a connection from the pool"

**Check:**

```ruby
# Current pool configuration
ActiveRecord::Base.connection_pool.instance_variable_get(:@size)

# Check in-use connections
pool = ActiveRecord::Base.connection_pool
puts "Size: #{pool.size}, Available: #{pool.instance_variable_get(:@available).instance_variable_get(:@queue).size}, Waiting: #{pool.instance_variable_get(:@num_waiting_in_queue)}"
```

**Solutions:**

- Increase `pool` in `database.yml`
- Add `checkout_timeout`
- Find long-running queries
- Use `ActiveRecord::Base.connection_pool.with_connection` properly

### External Service Timeout

```ruby
# Use timeouts for external calls
require 'timeout'

def fetch_with_timeout(url, timeout_sec = 5)
  Timeout.timeout(timeout_sec) do
    Net::HTTP.get(URI(url))
  end
rescue Timeout::Error
  Rails.logger.error "Request to #{url} timed out"
  nil
end

# Or with HTTP client gems
HTTP.timeout(5).get(url)
```

## Rails Issues

### Slow Request Debugging

```ruby
# Enable request logging
Rails.application.config.log_level = :debug

# Use rack-mini-profiler
gem 'rack-mini-profiler', group: :development

# Check request timing in logs
# Started GET "/users" for 127.0.0.1 at 2024-01-01 10:00:00
# Processing by UsersController#index as HTML
# Completed 200 OK in 245.3ms (Views: 123.4ms | ActiveRecord: 89.2ms)
```

### Memory Bloat in Production

```ruby
# Add to an initializer to track memory
if Rails.env.production?
  require 'objspace'
  
  Thread.new do
    loop do
      GC.start
      mem = `ps -o rss= -p #{Process.pid}`.to_i / 1024
      Rails.logger.info "Memory: #{mem}MB"
      sleep 60
    end
  end
end
```

### Database Connection Issues

```ruby
# Reconnect if connection lost
ActiveRecord::Base.connection.reconnect!

# Check connection health
ActiveRecord::Base.connection.active?

# Close idle connections
ActiveRecord::Base.connection_pool.flush!
```

## Quick Checklist

```markdown
## Troubleshooting: [Issue]

### Symptoms
- [ ] High memory?
- [ ] Slow responses?
- [ ] Timeouts?
- [ ] Crashes?

### Checked
- [ ] Rails logs: `tail -f log/production.log`
- [ ] Memory: Top processes, RSS usage
- [ ] Queries: Slow query log, missing indexes
- [ ] Jobs: Sidekiq queue depth and latency

### Root Cause
[...]

### Fix
[...]
```
