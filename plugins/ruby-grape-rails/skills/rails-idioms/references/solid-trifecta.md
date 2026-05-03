## Rails 8 Solid Trifecta

Rails 8 introduces three database-backed alternatives to Redis: Solid Queue, Solid Cache, and Solid Cable. They work with PostgreSQL or MySQL, eliminating Redis dependency for many apps.

### Solid Queue

Database-backed job queue that replaces Redis/Sidekiq for moderate throughput:

```ruby
# Gemfile
gem 'solid_queue'

# config/database.yml
production:
  primary:
    <<: *default
  queue:
    <<: *default
    database: myapp_queue
    migrations_paths: db/queue_migrate
```

```ruby
# config/environments/production.rb
config.active_job.queue_adapter = :solid_queue

# Optional: Run within Puma (single process)
config.solid_queue.connects_to = { database: { writing: :queue } }
```

Generate migrations + run worker (separate process recommended in
production):

```bash
bin/rails solid_queue:install
bin/jobs
```

#### Solid Queue vs Sidekiq Decision Matrix

| Factor | Solid Queue | Sidekiq |
|--------|-------------|---------|
| Throughput | ~1,000 jobs/sec | ~10,000+ jobs/sec |
| Latency | Higher (DB polling) | Lower (Redis pub/sub) |
| Monitoring | Basic Rails UI | Rich Sidekiq Web UI |
| Complexity | One less service | Requires Redis |
| Best for | Most apps | High-throughput, complex workflows |

**Use Solid Queue when:**

- Throughput < 1,000 jobs/sec
- You want fewer moving parts
- You already use PostgreSQL/MySQL
- Basic job retry/monitoring is sufficient

**Use Sidekiq when:**

- High throughput needed
- Complex job workflows
- Rich job metrics required
- Already invested in Redis infrastructure

### Solid Cache

Database-backed caching that replaces Redis/Memcached:

```ruby
# Gemfile
gem 'solid_cache'

# config/database.yml
production:
  primary:
    <<: *default
  cache:
    <<: *default
    database: myapp_cache
    migrations_paths: db/cache_migrate
```

```ruby
# config/environments/production.rb
config.cache_store = :solid_cache_store

# Configuration options
config.solid_cache.ttl = 1.week
config.solid_cache.max_entries = 10_000_000
```

Generate migrations: `bin/rails solid_cache:install`.

#### Solid Cache Patterns

```ruby
# Standard Rails caching works unchanged
Rails.cache.fetch("user/#{user_id}/stats", expires_in: 1.hour) do
  calculate_stats(user_id)
end

# Cache with tags (Solid Cache supports cache versioning)
Rails.cache.fetch("products/popular", version: Product.maximum(:updated_at)) do
  Product.popular.to_a
end

# Expire by pattern (using SQL)
SolidCache::Entry.where("key LIKE ?", "products/%").delete_all
```

### Solid Cable

Database-backed Action Cable that replaces Redis for WebSockets:

```ruby
# Gemfile
gem 'solid_cable'

# config/database.yml
production:
  primary:
    <<: *default
  cable:
    <<: *default
    database: myapp_cable
    migrations_paths: db/cable_migrate
```

```ruby
# config/cable.yml
production:
  adapter: solid_cable
  connects_to:
    database:
      writing: cable
```

Generate migrations: `bin/rails solid_cable:install`.

#### Solid Cable Limitations

- Slightly higher latency than Redis pub/sub
- Good for: Chat, notifications, live updates
- Consider Redis when: Real-time gaming, high-frequency trading updates

### Solid Trifecta Database Setup

Use separate databases for production:

```yaml
# config/database.yml
production:
  primary: &primary
    adapter: postgresql
    encoding: unicode
    pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
    url: <%= ENV['DATABASE_URL'] %>
  
  queue:
    <<: *primary
    url: <%= ENV['QUEUE_DATABASE_URL'] || ENV['DATABASE_URL'] %>
    migrations_paths: db/queue_migrate
  
  cache:
    <<: *primary
    url: <%= ENV['CACHE_DATABASE_URL'] || ENV['DATABASE_URL'] %>
    migrations_paths: db/cache_migrate
  
  cable:
    <<: *primary
    url: <%= ENV['CABLE_DATABASE_URL'] || ENV['DATABASE_URL'] %>
    migrations_paths: db/cable_migrate
```

Or use schemas in a single database:

```yaml
production:
  primary:
    adapter: postgresql
    database: myapp_production
  
  queue:
    adapter: postgresql
    database: myapp_production
    schema_search_path: queue
    migrations_paths: db/queue_migrate
```
