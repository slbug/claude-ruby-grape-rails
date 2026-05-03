# Quick Debug Commands & Common Fixes

## Quick Debug Commands

| Goal | Command |
|---|---|
| Safer rebuild sequence (cache-corruption suspected) | `bundle exec rails tmp:cache:clear && bundle install && bundle exec rake assets:precompile` |
| List methods matching a pattern on a class | `bundle exec rails runner "puts User.methods.grep(/find/).inspect"` |
| Interactive debugging | `bundle exec rails console` (then `reload!` to refresh code) |
| Run single test with output | `bundle exec rspec spec/models/user_spec.rb:42 -fd` |

## Common Fixes

### String vs Atom Keys

```ruby
# External data (JSON, params) = strings
params["key"]

# Internal data = atoms
struct.field
map.key
```

### Missing Eager Load

```ruby
# Before
user = User.find(id)
user.orders  # N+1 query issue

# After
user = User.includes(:orders).find(id)
```

### Nil Propagation

```ruby
# Before
user.profile.name  # Crashes if profile nil

# After (using safe navigation operator)
user.profile&.name

# Or using try
user.profile.try(:name)

# Or using dig for nested hashes
user.dig(:profile, :name)
```

## Logging-Based Debugging

When runtime tooling is unavailable, use Rails logs to diagnose
performance and behavior issues:

```ruby
# Enable verbose query logging in console
ActiveRecord::Base.logger = Logger.new(STDOUT)

# Or in a specific block
ActiveRecord::Base.connection_pool.with_connection do
  old_logger = ActiveRecord::Base.logger
  ActiveRecord::Base.logger = Logger.new(STDOUT)
  # Your code here
  ActiveRecord::Base.logger = old_logger
end
```

### Common Log Analysis

| What to Look For | How to Find It |
|------------------|----------------|
| N+1 Queries | Look for repeated same query with different IDs |
| Slow Queries | Look for query time > 100ms |
| Missing Indexes | Full table scan warnings |
| Cache Hits/Misses | Rails.cache.fetch logs |
| Sidekiq Job Failures | sidekiq.log or worker logs |

### Rails Panel / Bullet Gem

Add to Gemfile for real-time query analysis in development:

```ruby
group :development do
  gem 'bullet'  # Detects N+1 queries and unused eager loading
  gem 'rack-mini-profiler'  # Request profiling
end
```
