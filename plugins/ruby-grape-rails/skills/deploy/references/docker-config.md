# Docker Configuration Reference

## Multi-Stage Build

```dockerfile
# Dockerfile
FROM ruby:3.3-slim-bookworm AS builder

# Install build dependencies
RUN apt-get update -qq && \
    apt-get install -y build-essential libpq-dev libvips git && \
    apt-get clean

WORKDIR /rails

# Install bundler
RUN gem install bundler:2.5.0

# Copy Gemfile and install gems
COPY Gemfile Gemfile.lock ./
RUN bundle config set --local deployment 'true' && \
    bundle config set --local without 'development test' && \
    bundle install

# Copy application
COPY . .

# Precompile assets
RUN SECRET_KEY_BASE=dummy RAILS_ENV=production bundle exec rails assets:precompile

# Prefer targeted cleanup to broad recursive deletion
RUN bundle clean --force && \
    bundle exec rails tmp:clear

# Runner stage
FROM ruby:3.3-slim-bookworm AS runner

# Install runtime dependencies
RUN apt-get update -qq && \
    apt-get install -y libpq-dev libvips curl && \
    apt-get clean

# Create non-root user
RUN groupadd -r rails && useradd -r -g rails rails

WORKDIR /rails

# Copy from builder
COPY --from=builder /rails /rails
COPY --from=builder /usr/local/bundle /usr/local/bundle

# Set ownership
RUN chown -R rails:rails /rails

USER rails:rails

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000/up || exit 1

EXPOSE 3000

CMD ["bundle", "exec", "puma", "-C", "config/puma.rb"]
```

## Docker Compose (Development)

```yaml
# docker-compose.yml
version: '3.8'
services:
  app:
    build: .
    command: bundle exec rails s -p 3000 -b '0.0.0.0'
    volumes:
      - .:/rails
      - bundle_cache:/usr/local/bundle
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgres://postgres:password@db:5432/myapp_development
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    stdin_open: true
    tty: true

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=password
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  sidekiq:
    build: .
    command: bundle exec sidekiq
    volumes:
      - .:/rails
      - bundle_cache:/usr/local/bundle
    environment:
      - DATABASE_URL=postgres://postgres:password@db:5432/myapp_development
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

volumes:
  postgres_data:
  redis_data:
  bundle_cache:
```

## Docker Compose (Production)

```yaml
# docker-compose.production.yml
version: '3.8'
services:
  app:
    build:
      context: .
      target: runner
    environment:
      - RAILS_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - SECRET_KEY_BASE=${SECRET_KEY_BASE}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - db
      - redis
    deploy:
      replicas: 2
      resources:
        limits:
          memory: 512M
        reservations:
          memory: 256M

  sidekiq:
    build:
      context: .
      target: runner
    command: bundle exec sidekiq -C config/sidekiq.yml
    environment:
      - RAILS_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - db
      - redis
    deploy:
      resources:
        limits:
          memory: 256M

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

## Migration in Production

```ruby
# lib/tasks/release.rake
namespace :release do
  desc "Run post-deployment tasks"
  task deploy: :environment do
    Rake::Task["db:migrate"].invoke
    Rake::Task["db:seed"].invoke if ENV["SEED_ON_DEPLOY"]
    # Warm caches, etc.
  end
end
```

```bash
#!/bin/sh
# bin/release.sh
set -e

echo "Running migrations..."
bundle exec rails db:migrate

echo "Clearing cache..."
bundle exec rails runner "Rails.cache.clear"

echo "Release complete!"
```

## .dockerignore

```
# .dockerignore
.git
.gitignore
.github
README.md
Dockerfile
.dockerignore
docker-compose*.yml

# Rails
.env
.env.*
config/master.key
tmp
log
node_modules
vendor/bundle
public/assets
public/packs
storage

# Test
coverage
doc
spec
test

# Development
.bundle
.ruby-version
bin/spring
devbox.github
```

## Health Check Endpoint

```ruby
# config/routes.rb
Rails.application.routes.draw do
  # Health check endpoint for load balancers
  get "/up", to: "health#index"
  
  # Deep health check including database
  get "/health", to: "health#detailed"
end

# app/controllers/health_controller.rb
class HealthController < ActionController::Base
  rescue_from(Exception) { render_down }

  def index
    render json: { status: "ok", version: Rails.version }
  end

  def detailed
    checks = {
      database: database_check,
      redis: redis_check,
      storage: storage_check
    }
    
    all_ok = checks.values.all? { |v| v[:status] == "ok" }
    
    status = all_ok ? :ok : :service_unavailable
    render json: { status: all_ok ? "ok" : "error", checks: checks }, status: status
  end

  private

  def database_check
    ActiveRecord::Base.connection.execute("SELECT 1")
    { status: "ok", latency_ms: 0 }
  rescue => e
    { status: "error", message: e.message }
  end

  def redis_check
    Rails.cache.redis.ping
    { status: "ok" }
  rescue => e
    { status: "error", message: e.message }
  end

  def storage_check
    ActiveStorage::Blob.service.exist?("health-check")
    { status: "ok" }
  rescue => e
    { status: "error", message: e.message }
  end

  def render_down
    render json: { status: "error" }, status: :service_unavailable
  end
end
```
