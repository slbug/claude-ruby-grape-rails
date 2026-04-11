---
name: sidekiq
description: Sidekiq job design for Ruby apps using Rails, Active Record, or Sequel. Covers JSON-safe args, idempotency, retries, testing, and commit-safe enqueue patterns. Sidekiq 6.x through 8.x and Solid Queue.
user-invocable: false
effort: medium
paths:
  - app/jobs/**
  - app/workers/**
  - app/sidekiq/**
  - config/sidekiq.yml
  - "**/app/jobs/**"
  - "**/app/workers/**"
  - "**/app/sidekiq/**"
---
# Sidekiq

## Iron Laws

1. **Jobs are idempotent** - Safe to retry multiple times
2. **Pass IDs and JSON primitives only** - Never pass ORM objects
3. **Enqueue after commit** - Use the active ORM's commit-safe hook, not `after_save` or inline before commit
4. **Keep queue names intentional** - Operationally meaningful
5. **Use retries intentionally** - Don't hide permanent failures
6. **Profile slow jobs** - Use Sidekiq 8 profiling
7. **Iterate large datasets** - Use Sidekiq::Iteration

## Version Compatibility

| Sidekiq | Rails | Redis | Key Features |
|---------|-------|-------|--------------|
| 6.x | 6+ | 4.0+ | Basic processing |
| 7.x | 7+ | 6.2+ | Capsules, metrics |
| 8.x | 7+ | 7.0+ | Profiling, iteration, Valkey |

## Job Template

```ruby
class MyJob
  include Sidekiq::Job

  sidekiq_options queue: 'default', retry: 3

  def perform(user_id)
    user = User.find(user_id)
    # Do work
  end
end
```

## JSON-Safe Arguments

**✅ Correct:**

```ruby
MyJob.perform_async(user.id)                    # IDs
MyJob.perform_async(123, "string", true)        # Primitives
MyJob.perform_async(user.created_at.iso8601)    # Dates as strings
```

**❌ Incorrect:**

```ruby
MyJob.perform_async(user)              # ORM objects
MyJob.perform_async(Date.today)        # Date objects
MyJob.perform_async(status: :active)   # Symbols
```

## Idempotency

Jobs must be safe to run multiple times:

```ruby
class ProcessPaymentJob
  include Sidekiq::Job

  def perform(payment_id)
    payment = Payment.find(payment_id)
    return if payment.processed?  # State check
    
    payment.with_lock do
      return if payment.processed?  # Double-check
      payment.process!
    end
  end
end
```

**Strategies:** State check | Upsert | UUID dedup | Locking

## Commit-Safe Enqueueing by ORM

Always identify the ORM for the touched package before giving enqueue advice.

### Active Record

Use `after_commit` for model-driven enqueueing that depends on committed data:

```ruby
class User < ApplicationRecord
  after_commit :enqueue_welcome_email, on: :create

  private

  def enqueue_welcome_email
    WelcomeEmailJob.perform_async(id)
  end
end
```

### Sequel

Prefer transaction-level hooks when the enqueue depends on an explicit transaction:

```ruby
DB.transaction do
  user = User.create(name: 'Ada')
  DB.after_commit { WelcomeEmailJob.perform_async(user.id) }
end
```

Model-level hooks can work too, but they are still Sequel hooks, not Active Record callbacks:

```ruby
class User < Sequel::Model
  def after_commit
    super
    WelcomeEmailJob.perform_async(id)
  end
end
```

### Mixed ORM Repos

- identify the owning package first
- do not recommend Active Record callbacks inside Sequel packages
- do not assume every migration/job/model in the repo follows the same ORM lifecycle

## Enqueue After Commit

Always scope this advice to the package's owning ORM.

**Wrong:** Job may run before commit

```ruby
after_save :enqueue_welcome_email  # DANGEROUS
def enqueue_welcome_email
  WelcomeEmailJob.perform_async(id)
end
```

**Correct for Active Record:** Job runs after successful commit

```ruby
after_commit :enqueue_welcome_email, on: :create
def enqueue_welcome_email
  WelcomeEmailJob.perform_async(id)
end
```

**Correct for Sequel:** Use a transaction-level or Sequel model commit hook, not Active Record callbacks

```ruby
DB.transaction do
  user = User.create(name: 'Ada')
  DB.after_commit { WelcomeEmailJob.perform_async(user.id) }
end
```

## Queue Strategy

Use operationally meaningful names:

```ruby
# config/initializers/sidekiq.rb
Sidekiq.configure_server do |config|
  config.queues = %w[critical high default low]
  
  # Separate capsule for rate-limited work
  config.capsule("webhooks") do |cap|
    cap.concurrency = 5
    cap.queues = %w[webhooks]
  end
end
```

## Retry Strategy

```ruby
sidekiq_options retry: 5        # Custom count
sidekiq_options retry: false    # Disable retries

# Custom retry logic
sidekiq_retry_in do |count, exception|
  case exception
  when RateLimitError
    60 * (count + 1)           # Linear backoff
  when InvalidDataError
    :discard                   # Don't retry
  else
    nil                        # Default exponential
  end
end
```

## Sidekiq 8 Features

### Profiling

```ruby
sidekiq_options profile: 'mike'  # Profile in Web UI
```

### Iteration (Large Datasets)

```ruby
class ProcessUsersJob
  include Sidekiq::Job
  include Sidekiq::Iteration

  def build_enumerator(cursor:)
    User.active.cursor_rows(cursor: cursor)
  end

  def each_iteration(user)
    user.process!
  end
end
```

### Valkey Support

```ruby
config.redis = { url: ENV['VALKEY_URL'] || ENV['REDIS_URL'] }
```

## Testing

```ruby
# Inline execution
MyJob.new.perform(user.id)

# With testing mode
require 'sidekiq/testing'
Sidekiq::Testing.inline!

# Assert enqueued (Sidekiq-native)
expect {
  User.create!(name: "Test")
}.to change(MyJob.jobs, :size).by(1)
```

## Error Handling

```ruby
# Retry dead jobs
job = Sidekiq::DeadSet.new.find_job(jid)
job.retry

# Error tracking
config.error_handlers << ->(ex, context) {
  Bugsnag.notify(ex) { |e| e.add_metadata(:sidekiq, context) }
}
```

## Monitoring

```ruby
# config/routes.rb
require 'sidekiq/web'
authenticate :user, lambda { |u| u.admin? } do
  mount Sidekiq::Web => '/sidekiq'
end
```

## Solid Queue (Rails 8 Alternative)

Database-backed alternative to Redis:

| Feature | Sidekiq | Solid Queue |
|---------|---------|-------------|
| Backend | Redis/Valkey | PostgreSQL/MySQL |
| Performance | 10,000+ jobs/sec | 1,000+ jobs/sec |
| Complexity | Separate service | Built-in |
| Monitoring | Rich Web UI | Mission Control |

### Solid Queue Configuration

```ruby
# config/application.rb
config.active_job.queue_adapter = :solid_queue

# Concurrency limits (Rails 8.1+)
class ApiSyncJob < ApplicationJob
  limits_concurrency to: 5, key: ->(user_id) { user_id }
end

# Transaction safety (Rails 8+)
class MyJob < ApplicationJob
  self.enqueue_after_transaction_commit = true
end
```

### Recurring Tasks

```yaml
# config/recurring.yml
production:
  daily_cleanup:
    class: DailyCleanupJob
    schedule: every day at 2am
```

### Stringify Keys

```ruby
# Arguments come in stringified
metadata["user_agent"]  # NOT metadata[:user_agent]

# When enqueuing
ProcessOrderJob.perform_later(order.id, hash.stringify_keys)
```

### ActiveJob::Continuable (Rails 8.1+)

For long-running jobs that exceed timeout limits, use `ActiveJob::Continuable` to break work into resumable steps:

```ruby
class ProcessLargeDatasetJob < ApplicationJob
  include ActiveJob::Continuable

  def perform
    step :setup do
      @users = User.order(:id)
    end

    step(:process_batch) do |step|
      @users.find_each(start: step.cursor) do |user|
        process_user(user)
        step.advance! from: user.id
      end
    end

    step :cleanup
  end

  def cleanup
    # Final cleanup work
  end

  private

  def process_user(user)
    # Process individual record
  end
end
```

**Benefits:**

- Prevents job timeouts on large datasets
- Job automatically resumes from last checkpoint after interruption
- Each step has its own retry semantics
- Natural fit for Sidekiq's retry model
- Progress is preserved even if worker restarts

**Use when:** Processing large datasets, bulk imports, or any work that exceeds typical job timeout limits (e.g., 25 seconds on Heroku, configurable elsewhere).

See: [ActiveJob::Continuation Documentation](https://api.rubyonrails.org/classes/ActiveJob/Continuation.html)

## Best Practices Summary

1. Use IDs, not objects
2. Make jobs idempotent
3. Use the active ORM's commit-safe enqueue hook
4. Limit concurrency for external APIs
5. Enable `enqueue_after_transaction_commit` when using Rails Active Job
6. Stringify hash keys
7. Monitor queue depth
8. Set appropriate retry counts

## References

- `references/idempotency-patterns.md` — Detailed idempotency strategies
- `references/iteration-patterns.md` — Sidekiq::Iteration deep dive
- `references/solid-queue-migration.md` — Migrating from Sidekiq to Solid Queue
- `references/performance-tuning.md` — Profiling and optimization
