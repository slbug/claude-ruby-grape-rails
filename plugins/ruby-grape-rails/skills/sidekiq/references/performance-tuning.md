# Sidekiq Performance Tuning

## Profiling with Sidekiq 8

```ruby
class SlowJob
  include Sidekiq::Job

  sidekiq_options profile: 'mike'

  def perform(user_id)
    # Slow work here
  end
end
```

View in Web UI under "Profiles":

- CPU time breakdown
- Memory allocation
- Method call frequencies
- Hot path identification

## When to Profile

- Jobs taking > 1 second
- High memory usage
- Database query optimization
- Before/after optimization

## Connection Pool Tuning

```ruby
# config/initializers/sidekiq.rb
Sidekiq.configure_server do |config|
  # Match concurrency to database pool
  config.concurrency = 10
  
  # Separate pools for different workloads
  config.capsule("io") do |cap|
    cap.concurrency = 20  # IO-bound work
    cap.queues = %w[webhooks emails]
  end
  
  config.capsule("cpu") do |cap|
    cap.concurrency = 5   # CPU-bound work
    cap.queues = %w[reports exports]
  end
end
```

## Redis Optimization

```ruby
# Use Redis pipelining for bulk operations
Sidekiq::Client.push_bulk('class' => MyJob, 'args' => user_ids.map { |id| [id] })
```
