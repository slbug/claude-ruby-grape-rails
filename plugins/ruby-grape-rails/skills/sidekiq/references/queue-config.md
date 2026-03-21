# Sidekiq Configuration Reference

## Basic Configuration

```ruby
# config/initializers/sidekiq.rb
Sidekiq.configure_server do |config|
  config.redis = { url: ENV.fetch('REDIS_URL', 'redis://localhost:6379/0') }
  
  # Server-side middleware
  config.server_middleware do |chain|
    chain.add Sidekiq::Middleware::Server::RetryJobs, max_retries: 5
  end
end

Sidekiq.configure_client do |config|
  config.redis = { url: ENV.fetch('REDIS_URL', 'redis://localhost:6379/0') }
end
```

## Queue Configuration

```ruby
# config/sidekiq.yml
:concurrency: 25
:queues:
  - critical
  - mailers
  - webhooks
  - media_processing
  - external_api
  - imports
  - default

:limits:
  external_api: 5
  media_processing: 3
```

## Queue Design Principles

- **I/O vs CPU bound** — Separate queues prevent CPU work from blocking I/O
- **External dependencies** — Different APIs get isolated queues
- **Priority separation** — Critical jobs in dedicated high-concurrency queue
- **Rate limiting** — Queue-level limits for API respect

## Connection Pool Sizing

```ruby
# Redis pool should be >= (concurrency + 2) * num_processes
# For 25 threads: pool_size of 25 + 2 = 27 minimum
```

## Cron Scheduling (with sidekiq-cron)

```ruby
# Gemfile
gem 'sidekiq-cron'

# config/initializers/sidekiq.rb
Sidekiq::Cron::Job.create(
  name: 'Hourly Worker',
  cron: '0 * * * *',
  class: 'HourlyWorker'
)

Sidekiq::Cron::Job.create(
  name: 'Daily Worker',
  cron: '0 0 * * *',
  class: 'DailyWorker'
)
```

## Production Checklist

- [ ] Redis connection pool sized correctly
- [ ] Retry configuration set (default: 25, usually too high - reduce to 3-5)
- [ ] Dead job queue monitored
- [ ] Error tracking integrated (Sentry, Honeybadger, etc.)
- [ ] Graceful shutdown period set (config term_timeout)
- [ ] Unique constraints on user-triggered jobs (with sidekiq-unique-jobs)
- [ ] All jobs handle exceptions explicitly
- [ ] Idempotency for critical operations (payments, emails)

## Advanced Configuration

```ruby
# config/initializers/sidekiq.rb
Sidekiq.configure_server do |config|
  # Graceful shutdown - wait up to 25 seconds for jobs to finish
  config[:term_timeout] = 25
  
  # Custom error handler
  config.error_handlers << ->(ex, context) {
    Sentry.capture_exception(ex, extra: context)
  }
  
  # Lifecycle events
  config.on(:startup) do
    # Warm up connections, etc.
  end
  
  config.on(:shutdown) do
    # Cleanup
  end
end
```

## Monitoring

```ruby
# config/routes.rb
require 'sidekiq/web'
mount Sidekiq::Web => '/sidekiq'
```

## Redis Configuration

```ruby
# For high availability, use Redis Sentinel or Redis Cluster
Sidekiq.configure_server do |config|
  config.redis = {
    url: ENV['REDIS_URL'],
    sentinel_master: 'mymaster',
    sentinels: [
      { host: 'sentinel1', port: 26379 },
      { host: 'sentinel2', port: 26379 }
    ]
  }
end
```

## Deployment

```yaml
# docker-compose.yml or kubernetes config
version: '3'
services:
  sidekiq:
    build: .
    command: bundle exec sidekiq -C config/sidekiq.yml
    environment:
      - REDIS_URL=redis://redis:6379/0
      - RAILS_ENV=production
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M
```
