# Job Patterns Reference

> **Note**: Sidekiq 7.x+ uses `Sidekiq::Job` instead of legacy `Sidekiq::Worker`

## Basic Job

```ruby
class EmailJob
  include Sidekiq::Job
  
  sidekiq_options queue: 'mailers', retry: 5

  def perform(user_id, email_type)
    user = User.find(user_id)
    UserMailer.with(user: user).send(email_type).deliver_now
  end
end
```

## Job Options

```ruby
class ImportJob
  include Sidekiq::Job
  
  sidekiq_options(
    queue: 'imports',
    retry: 3,                    # Retries before dead queue
    backtrace: 5,                # Lines of backtrace to keep
    tags: ['import', 'csv'],     # For filtering/monitoring
    lock: :until_executed,       # With sidekiq-unique-jobs
    lock_ttl: 1.hour
  )

  def perform(import_id)
    import = Import.find(import_id)
    CsvImporter.new(import).process
  end
end
```

## Unique Jobs (Deduplication)

Using `sidekiq-unique-jobs` gem:

```ruby
class NotificationJob
  include Sidekiq::Job
  
  sidekiq_options(
    lock: :until_executed,         # Lock until job completes
    lock_ttl: 5.minutes,           # Lock expires after 5 min
    unique_args: ->(args) { [args[0]] }  # Only dedupe on user_id
  )

  def perform(user_id, message)
    user = User.find(user_id)
    user.notifications.create!(message: message)
  end
end
```

## Custom Backoff

```ruby
class ApiCallJob
  include Sidekiq::Job
  
  sidekiq_options retry: 5

  def perform(endpoint, params)
    response = HttpClient.post(endpoint, params)
    raise ApiError, response.body unless response.success?
  end
  
  # Custom retry delay - exponential with jitter
  sidekiq_retry_in do |count, exception|
    case exception
    when ApiError
      (count ** 4) + 15 + rand(30)  # 16, 31, 96, 271... seconds
    else
      count * 10  # Default: 10, 20, 30... seconds
    end
  end
end
```

## Idempotency Pattern

```ruby
class ChargeJob
  include Sidekiq::Job

  sidekiq_options queue: 'payments', retry: 3

  def perform(user_id, amount_cents, idempotency_key)
    # Load user record
    user = User.find(user_id)

    # Check for existing charge with this key
    existing = Payment.find_by(idempotency_key: idempotency_key)
    return existing if existing

    # Create new charge record
    payment = Payment.create!(
      user_id: user_id,
      amount_cents: amount_cents,
      idempotency_key: idempotency_key,
      status: 'pending'
    )

    # Process charge with Stripe
    Stripe::Charge.create(
      amount: amount_cents,
      currency: 'usd',
      customer: user.stripe_customer_id,
      idempotency_key: idempotency_key
    )

    payment.update!(status: 'succeeded')
  rescue Stripe::CardError => e
    # Log and don't retry - card errors are final
    Rails.logger.error("Card declined: #{e.message}")
    payment.update!(status: 'failed', error: e.message)
  end
end
```

## Error Handling & Monitoring

```ruby
# config/initializers/sidekiq.rb
Sidekiq.configure_server do |config|
  # Sentry integration
  config.error_handlers << ->(ex, context) {
    Sentry.capture_exception(ex, 
      extra: context,
      tags: { job: context[:job]['class'] }
    )
  }
  
  # Custom retry exhausted handler
  config.death_handlers << ->(job, ex) {
    Rails.logger.error("Job #{job['jid']} exhausted retries: #{ex.message}")
    FailedJobNotificationMailer.notify(job, ex).deliver_later
  }
end
```

## Runtime Queue Control

```ruby
# Clear specific queue (standard Sidekiq API)
Sidekiq::Queue['imports'].clear

# Get queue size (standard Sidekiq API)
Sidekiq::Queue['mailers'].size

# Note: Queue pause/resume requires Sidekiq Enterprise or custom middleware
# Standard Sidekiq does not provide pause/unpause on Sidekiq::Queue
```

## Batch Jobs (with sidekiq-batch)

```ruby
class ImportBatchJob
  include Sidekiq::Job

  def perform(import_id)
    import = Import.find(import_id)
    
    batch = Sidekiq::Batch.new
    batch.description = "Import #{import.id}"
    batch.on(:success, ImportCallback, import_id: import.id)
    
    batch.jobs do
      import.rows.each do |row|
        RowImportJob.perform_async(row.id)
      end
    end
  end
end

class ImportCallback
  def on_success(status, options)
    import = Import.find(options['import_id'])
    import.update!(status: 'completed')
    ImportMailer.completed(import).deliver_later
  end
end
```

## Anti-patterns

```ruby
# ❌ Complex objects in args (JSON roundtrip fails)
def perform(user)
  user.do_something  # Won't work - user is a Hash, not User instance
end

# ✅ Just the ID
def perform(user_id)
  user = User.find(user_id)
  user.do_something
end

# ❌ Large data in args
# { file_content: large_binary }

# ✅ Store reference, pass ID
# { file_path: "/uploads/abc123.csv" }

# ❌ Silent failures
def perform(email)
  Mailer.send(email)  # Ignores return value!
end

# ✅ Handle all outcomes
def perform(email)
  result = Mailer.send(email)
  raise MailError, result.error unless result.success?
end

# ❌ No error handling for external APIs
def perform(user_id)
  Stripe::Charge.create(...)  # Will retry forever on card errors
end

# ✅ Distinguish retryable vs final errors
def perform(user_id)
  begin
    Stripe::Charge.create(...)
  rescue Stripe::CardError => e
    # Card errors are final - don't retry
    handle_final_error(e)
  end
end
```

## Best Practices

1. **Always pass IDs, not objects** - Sidekiq serializes to JSON
2. **Keep jobs idempotent** - They may run multiple times
3. **Handle expected errors** - Don't retry card declines, validation errors
4. **Use separate queues** - Don't block critical jobs with slow imports
5. **Set appropriate retry counts** - Default 25 is usually too high
6. **Monitor dead queue** - Failed jobs accumulate there
7. **Test jobs synchronously** - Use `perform_inline` in tests
8. **Include job context in errors** - Makes debugging easier
