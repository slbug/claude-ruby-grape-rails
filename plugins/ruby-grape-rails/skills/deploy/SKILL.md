---
name: deploy
description: Ruby/Rails/Grape deployment guidance for Rails 8+ with Solid Trifecta, Thruster, Kamal 2, Docker, and cloud platforms. Covers migrations, assets, workers, and environment configuration.
user-invocable: false
effort: medium
paths:
  - Dockerfile
  - docker-compose.yml
  - config/deploy.rb
  - ".github/workflows/**"
  - "config/environments/**"
  - "**/Dockerfile"
  - "**/docker-compose.yml"
  - "**/config/deploy.rb"
  - "**/config/environments/**"
---
# Deploy

Deployment guidance for Ruby/Rails/Grape applications in the Rails 8 era.

## Deployment Architecture

### Rails 8 Deployment Stack

```
┌─────────────────────────────────────┐
│  Load Balancer (Cloudflare/AWS)     │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  Thruster (HTTP/2, TLS, Gzip)       │
│  - HTTP/2 support                   │
│  - Auto Let's Encrypt               │
│  - X-Sendfile                       │
│  - Gzip compression                 │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  Puma (App Server)                  │
│  - Workers: $WEB_CONCURRENCY        │
│  - Threads: $RAILS_MAX_THREADS      │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  Rails Application                  │
│  - Solid Queue (DB jobs)            │
│  - Solid Cache (DB cache)           │
│  - Solid Cable (DB websockets)      │
└─────────────┬───────────────────────┘
              │
┌─────────────▼───────────────────────┐
│  PostgreSQL / MySQL                 │
└─────────────────────────────────────┘
```

## Solid Trifecta

Rails 8's "Solid Trifecta" replaces Redis for most apps:

### Solid Queue

Database-backed job queue (replaces Sidekiq for many):

```ruby
# Gemfile
gem 'solid_queue'

# config/application.rb
config.active_job.queue_adapter = :solid_queue

# config/recurring.yml (recurring jobs)
production:
  periodic_cleanup:
    class: CleanupJob
    schedule: every day at 3am
```

### Solid Cache

Database-backed caching (replaces Redis/Memcached):

```ruby
# Gemfile
gem 'solid_cache'

# config/cache.yml
production:
  database: cache
  store_options:
    max_entries: 10000000
    max_size: 256.megabytes
```

### Solid Cable

Database-backed Action Cable (replaces Redis for websockets):

```ruby
# Gemfile
gem 'solid_cable'

# config/cable.yml
production:
  adapter: solid_cable
  polling_interval: 0.1.seconds
  keep_messages_around_for: 1.day
```

### Migration Guide: Redis to Solid

```ruby
# Before (Redis required)
# config/application.rb
config.active_job.queue_adapter = :sidekiq

# After (Database only)
config.active_job.queue_adapter = :solid_queue

# Run migrations
bundle exec rails solid_queue:install
bundle exec rails solid_cache:install
bundle exec rails solid_cable:install
bundle exec rails db:migrate
```

## Thruster

Thruster is the HTTP/2 proxy + Puma wrapper from 37signals:

### Installation

```dockerfile
# Dockerfile
FROM ruby:3.4-slim

# Install Thruster
COPY --from=ghcr.io/basecamp/thruster:latest /usr/local/bin/thrust /usr/local/bin/thrust

# ... Rails setup ...

CMD ["thrust", "bundle", "exec", "puma", "-C", "config/puma.rb"]
```

### Configuration

Thruster uses environment variables:

```
# Required
PORT=3000

# Optional
THRUSTER_TLS=true                    # Enable TLS
THRUSTER_TLS_DOMAIN=example.com      # Auto Let's Encrypt
THRUSTER_MAX_REQUEST_BODY=100MB      # Upload limit
THRUSTER_CACHE_SIZE=100MB            # HTTP cache
THRUSTER_X_SENDFILE=true             # Static file serving
```

### Benefits

- **HTTP/2**: Modern protocol support
- **Auto TLS**: Let's Encrypt integration
- **Zero config**: Environment variables only
- **X-Sendfile**: Efficient static file serving
- **Gzip**: Built-in compression

## Kamal 2

Kamal 2 is the zero-downtime Docker deployment tool:

### Configuration

```yaml
# config/deploy.yml
service: myapp
image: myuser/myapp

servers:
  web:
    - 192.168.1.1
    - 192.168.1.2
  job:
    hosts:
      - 192.168.1.3
    cmd: bundle exec solid_queue

registry:
  username: myuser
  password:
    - KAMAL_REGISTRY_PASSWORD

env:
  secret:
    - RAILS_MASTER_KEY
    - DATABASE_URL
  clear:
    RAILS_ENV: production
    WEB_CONCURRENCY: 4
    RAILS_MAX_THREADS: 5

# Thruster + Puma
builder:
  args:
    RUBY_VERSION: 3.4.1

# Health checks
healthcheck:
  path: /up
  port: 3000
  max_attempts: 10
  interval: 5s
```

### Commands

- Setup servers: `kamal setup`
- Deploy: `kamal deploy`
- Rollback: `kamal rollback`
- Run command: `kamal app exec 'rails db:migrate'`
- View logs: `kamal logs`
- Console: `kamal app exec --interactive 'rails console'`

## Docker Deployment

### Multi-stage Dockerfile

```dockerfile
# Build stage
FROM ruby:3.4-slim AS builder

RUN apt-get update -qq && \
    apt-get install -y build-essential libpq-dev

WORKDIR /app
COPY Gemfile Gemfile.lock ./
RUN bundle config set --local deployment 'true' && \
    bundle config set --local without 'development test' && \
    bundle install

COPY . .

# Precompile assets (Propshaft)
RUN SECRET_KEY_BASE=dummy bundle exec rails assets:precompile

# Runtime stage
FROM ruby:3.4-slim

# Install runtime deps
RUN apt-get update -qq && \
    apt-get install -y libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Thruster
COPY --from=ghcr.io/basecamp/thruster:latest /usr/local/bin/thrust /usr/local/bin/thrust

WORKDIR /app

# Copy from builder
COPY --from=builder /app /app
COPY --from=builder /usr/local/bundle /usr/local/bundle

# Non-root user
RUN groupadd -r rails && useradd -r -g rails rails && \
    chown -R rails:rails /app
USER rails

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3000/up || exit 1

EXPOSE 3000

CMD ["thrust", "bundle", "exec", "puma", "-C", "config/puma.rb"]
```

## Migrations

### Safe Migration Practices

1. **Add column**: Safe, no lock
2. **Add index**: Use `algorithm: :concurrently` (PostgreSQL)
3. **Remove column**: First ignore column, then remove
4. **Change column**: Create new, backfill, swap, remove old

### Deployment Migration Strategy

```ruby
# 1. Deploy with migration
# Run before app servers restart
bundle exec rails db:migrate

# 2. Deploy app code
# Restart app servers

# 3. Post-deploy (if needed)
# Data backfills, cleanup
```

### Strong Migrations

```ruby
# Gemfile
gem 'strong_migrations'

# config/initializers/strong_migrations.rb
StrongMigrations.enabled = true
StrongMigrations.target_version = 10  # PostgreSQL version
```

## Assets

### Propshaft (Rails 8 Default)

```ruby
# Gemfile
gem 'propshaft'

# No config needed for basic usage!
```

### Asset Precompilation

```dockerfile
# In Dockerfile
RUN SECRET_KEY_BASE=dummy bundle exec rails assets:precompile
```

### CDN Configuration

```ruby
# config/environments/production.rb
config.asset_host = ENV['CDN_HOST']
config.assets.compile = false
```

## Environment Configuration

### Required Environment Variables

```
# Rails
RAILS_ENV=production
RAILS_MASTER_KEY=xxxxxxxxxxxx
SECRET_KEY_BASE=xxxxxxxxxxxx

# Database
DATABASE_URL=postgresql://user:pass@host/db

# Optional (Solid Trifecta needs no Redis!)
# Only add if using Sidekiq/Redis
REDIS_URL=redis://host:6379/0

# Thruster/Puma
PORT=3000
WEB_CONCURRENCY=4
RAILS_MAX_THREADS=5

# Logging
RAILS_LOG_TO_STDOUT=true
RAILS_SERVE_STATIC_FILES=true
```

### Secrets Management

- Rails credentials (preferred): `EDITOR=vim bundle exec rails credentials:edit`
- Or environment variables: `export RAILS_MASTER_KEY=$(cat config/master.key)`

## Web vs Worker Separation

### Traditional (Sidekiq + Redis)

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    command: thrust bundle exec puma
    ports:
      - "3000:3000"
    environment:
      - REDIS_URL=redis://redis:6379
  
  worker:
    build: .
    command: bundle exec sidekiq
    environment:
      - REDIS_URL=redis://redis:6379
  
  redis:
    image: redis:7-alpine
```

### Modern (Solid Queue)

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    command: thrust bundle exec puma
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgresql://postgres@db/myapp
  
  worker:
    build: .
    command: bundle exec solid_queue
    environment:
      - DATABASE_URL=postgresql://postgres@db/myapp
  
  db:
    image: postgres:16-alpine
```

## Health Checks

### Rails Health Endpoint

```ruby
# config/routes.rb
get "up" => "rails/health#show", as: :rails_health_check
```

### Kubernetes

```yaml
# deployment.yaml
livenessProbe:
  httpGet:
    path: /up
    port: 3000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /up
    port: 3000
  initialDelaySeconds: 5
  periodSeconds: 10
```

### Docker Compose

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/up"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```

## Cloud Platform Guides

See: [references/cloud-platforms.md](references/cloud-platforms.md) — Heroku, AWS ECS, Fly.io, Kubernetes configs

## Monitoring & Observability

See: [references/docker-config.md](references/docker-config.md) — Health checks, logging, and monitoring setup

## Checklist

Before deploying:

- [ ] Database migrations tested locally
- [ ] Assets precompile successfully
- [ ] Health check endpoint responds
- [ ] Environment variables configured
- [ ] Secrets/credentials set
- [ ] Docker image builds
- [ ] Rollback plan ready
- [ ] Monitoring in place
