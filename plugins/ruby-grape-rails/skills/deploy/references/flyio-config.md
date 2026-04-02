# Fly.io Configuration Reference

## fly.toml

```toml
app = "my-app"
primary_region = "iad"

[build]
  dockerfile = "Dockerfile"

[deploy]
  release_command = "bundle exec rails db:migrate"
  strategy = "rolling"

[env]
  RAILS_LOG_TO_STDOUT = "enabled"
  RAILS_SERVE_STATIC_FILES = "enabled"
  RAILS_ENV = "production"
  PORT = "3000"

[http_service]
  internal_port = 3000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 1

  [http_service.concurrency]
    type = "connections"
    hard_limit = 1000
    soft_limit = 800

  [[http_service.checks]]
    interval = "15s"
    timeout = "2s"
    grace_period = "5s"
    method = "GET"
    path = "/up"
    protocol = "http"

[[vm]]
  cpu_kind = "shared"
  cpus = 1
  memory_mb = 512

[processes]
  app = "bundle exec puma -C config/puma.rb"
  sidekiq = "bundle exec sidekiq"
```

## Commands

```bash
# Create app
fly launch

# Set secrets
fly secrets set SECRET_KEY_BASE=$(rails secret)
fly secrets set RAILS_MASTER_KEY=$(cat config/master.key)
fly secrets set DATABASE_URL="postgres://..."
fly secrets set REDIS_URL="redis://..."

# Create Postgres
fly postgres create --name my-app-db
fly postgres attach my-app-db

# Create Redis (Upstash)
fly redis create

# Deploy
fly deploy

# SSH into running instance
fly ssh console --pty -C "bundle exec rails console"

# View logs
fly logs

# Scale
fly scale count 3
fly scale vm shared-cpu-2x

# Run migrations manually
fly ssh console -C "bundle exec rails db:migrate"

# Console access
fly ssh console -C "bundle exec rails console"
```

## Rails Production Configuration

```ruby
# config/environments/production.rb
Rails.application.configure do
  # Ensure proper logging
  config.logger = ActiveSupport::Logger.new(STDOUT)
    .tap { |logger| logger.formatter = Logger::Formatter.new }
    .then { |logger| ActiveSupport::TaggedLogging.new(logger) }

  # Cache in Redis
  config.cache_store = :redis_cache_store, {
    url: ENV.fetch("REDIS_URL") { "redis://localhost:6379/0" },
    pool_size: 5,
    pool_timeout: 5,
    reconnect_attempts: 3
  }

  # Active Storage (configure for S3 or other)
  config.active_storage.service = :amazon if ENV["AWS_ACCESS_KEY_ID"]

  # Action Cable in production
  config.action_cable.url = "wss://#{ENV['FLY_APP_NAME']}.fly.dev/cable"
  config.action_cable.allowed_request_origins = [
    "https://#{ENV['FLY_APP_NAME']}.fly.dev",
    /https:\/\/.*\.fly\.dev/
  ]
end
```

## Database Configuration

```yaml
# config/database.yml
production:
  adapter: postgresql
  encoding: unicode
  pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
  url: <%= ENV.fetch("DATABASE_URL") %>
  prepared_statements: false
```

## Puma Configuration for Fly.io

```ruby
# config/puma.rb
workers Integer(ENV.fetch('WEB_CONCURRENCY', 2))
threads_count = Integer(ENV.fetch('RAILS_MAX_THREADS', 5))
threads threads_count, threads_count

preload_app!

rackup DefaultRackup if defined?(DefaultRackup)
port ENV.fetch("PORT", 3000)
environment ENV.fetch("RAILS_ENV") { "development" }

on_worker_boot do
  ActiveRecord::Base.establish_connection if defined?(ActiveRecord)
end

# Health check plugin
plugin :tmp_restart
```

## Sidekiq Configuration

```yaml
# config/sidekiq.yml
:concurrency: <%= ENV.fetch("SIDEKIQ_CONCURRENCY", 5) %>
:queues:
  - critical
  - default
  - mailers
:limits:
  critical: 10
  mailers: 5
```

```ruby
# config/initializers/sidekiq.rb
Sidekiq.configure_server do |config|
  config.redis = { url: ENV.fetch("REDIS_URL") }
  
  # Database connection pool
  ActiveRecord::Base.establish_connection(
    ENV.fetch("DATABASE_URL")
  )
end

Sidekiq.configure_client do |config|
  config.redis = { url: ENV.fetch("REDIS_URL") }
end
```

## Fly.io Postgres with IPv6

```ruby
# config/database.yml
production:
  adapter: postgresql
  url: <%= ENV["DATABASE_URL"] %>
  # Fly Postgres uses IPv6
  host: <%= ENV["FLY_APP_NAME"] %>-db.internal
  # Or use the full URL with IPv6 support
```

## Deployment Hooks

```ruby
# lib/tasks/fly.rake
namespace :fly do
  task release: :environment do
    puts "Running release tasks..."
    
    # Run migrations
    Rake::Task["db:migrate"].invoke
    
    # Seed if first deploy
    if ActiveRecord::Base.connection.tables.empty?
      Rake::Task["db:seed"].invoke
    end
    
    puts "Release tasks complete!"
  end
end
```

## Monitoring on Fly.io

```ruby
# config/initializers/prometheus.rb (optional)
if ENV["FLY_ALLOC_ID"]
  require "prometheus/middleware/collector"
  require "prometheus/middleware/exporter"
  
  Rails.application.middleware.use Prometheus::Middleware::Collector
  Rails.application.middleware.use Prometheus::Middleware::Exporter
end
```

## CI/CD with GitHub Actions

```yaml
# Example workflow file in your app repo: .github/workflows/fly.yml
name: Fly Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    name: Deploy to Fly.io
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Ruby
        uses: ruby/setup-ruby@v1
        with:
          bundler-cache: true
      
      - name: Run tests
        run: bundle exec rspec
        env:
          RAILS_ENV: test
          DATABASE_URL: postgres://postgres:postgres@localhost:5432/test
      
      - name: Setup Flyctl
        uses: superfly/flyctl-actions/setup-flyctl@master
      
      - name: Deploy
        run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```
