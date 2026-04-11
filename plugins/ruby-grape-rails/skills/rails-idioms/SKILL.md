---
name: rails-idioms
description: Idiomatic Rails patterns for controllers, params, callbacks, jobs, and application structure. Load when working in `app/`, `config/routes.rb`, or service/controller boundaries across Rails 7.x and 8.x.
user-invocable: false
effort: medium
paths:
  - app/controllers/**
  - app/models/**
  - app/jobs/**
  - app/helpers/**
  - config/routes.rb
  - config/routes/**
  - "**/config/routes.rb"
  - "**/config/routes/**"
  - "**/app/controllers/**"
  - "**/app/models/**"
  - "**/app/helpers/**"
  - "**/app/jobs/**"
---
# Rails Idioms

## Iron Laws

1. Controllers orchestrate; they do not own domain logic.
2. Use explicit params shaping and authorization.
3. Keep callbacks boring; push external side effects to `after_commit` or application services.
4. Prefer built-in Rails capabilities before adding infrastructure gems.
5. **Use Sidekiq for high-throughput background jobs** (this plugin's recommended stack).
6. **Consider Solid Queue** for simpler ops when throughput needs are moderate (Rails 8 default).
7. **Choose cache/cable backends based on infrastructure** — Redis for multi-server, Solid for single-server simplicity.

## Overview

Rails 8 brings database-backed infrastructure (Solid Queue, Solid Cache, Solid Cable)
that eliminates Redis dependency for many applications. This skill covers modern Rails
patterns from Rails 7 through 8.x.

## Rails 8 Solid Stack

Rails 8 introduces three database-backed alternatives to Redis infrastructure:

| Component | Replaces | Best For |
|-----------|----------|----------|
| Solid Queue | Sidekiq/Redis | Moderate throughput, simpler ops |
| Solid Cache | Redis | Single-server or replicated setups |
| Solid Cable | Redis | Most real-time features |

See [Solid Trifecta Guide](references/solid-trifecta.md) for setup and migration.

## Quick Reference

### Controllers

```ruby
# Modern controller structure
class PostsController < ApplicationController
  before_action :set_post, only: [:show, :edit, :update, :destroy]
  before_action :authorize_post!, only: [:edit, :update, :destroy]
  
  def index
    @posts = Post.recent.includes(:author, :tags)
  end
  
  def create
    @post = Post.new(post_params)
    
    if @post.save
      redirect_to @post, notice: "Post created"
    else
      render :new, status: :unprocessable_entity
    end
  end
  
  private
  
  def post_params
    params.require(:post).permit(:title, :body, :published, tag_ids: [])
  end
end
```

See [Controllers Guide](references/controllers.md) for patterns and anti-patterns.

### Strong Parameters

```ruby
# Good: Explicit, whitelisted
params.require(:user).permit(:email, :name, settings: [:theme, :notifications])

# Bad: Unfiltered params access
User.create(params[:user])
```

### Callbacks

```ruby
# Good: Keep callbacks simple, use after_commit for external effects
class Order < ApplicationRecord
  after_create_commit :send_confirmation

  private

  def send_confirmation
    OrderMailer.confirmation(self).deliver_later
  end
end

# Bad: Complex logic in callbacks
class Order < ApplicationRecord
  after_create do
    # 50 lines of business logic
    # External API calls
    # Multiple side effects
  end
end
```

See [Callbacks Guide](references/callbacks.md) for patterns.

## Detailed Guides

- [Solid Trifecta](references/solid-trifecta.md) — Solid Queue, Cache, Cable setup
- [Authentication](references/authentication.md) — Rails 8 auth generator
- [Async Queries](references/async-queries.md) — Database-backed async processing
- [Propshaft](references/propshaft.md) — Modern asset pipeline
- [Thruster](references/thruster.md) — Zero-downtime deployments
- [Kamal 2](references/kamal2.md) — Container deployment
- [Controllers](references/controllers.md) — Modern controller patterns
- [Callbacks](references/callbacks.md) — Best practices and anti-patterns
- [Active Record Patterns](references/active-record-patterns.md) — Scopes, validations, transactions
- [Rails 8.1 Features](references/rails81-features.md) — Rails 8.1 features
- [Testing](references/testing.md) — Rails testing patterns
- [Anti-patterns](references/anti-patterns.md) — Common mistakes to avoid
- [Checklist](references/checklist.md) — Rails 8 migration checklist

## When to Use What

| Feature | Recommendation |
|---------|----------------|
| Job queue | Solid Queue for most; Sidekiq for high throughput |
| Caching | Solid Cache for single-server; Redis for distributed |
| Real-time | Solid Cable for most; Redis for massive scale |
| Auth | Rails 8 generator for new apps; Devise for complex needs |
| Assets | Propshaft for new apps; Sprockets for legacy |
| Deployment | Kamal 2 for VPS; Docker for complex orchestration |

## See Also

- [Active Record Patterns](../active-record-patterns/SKILL.md) — Database patterns
- [Hotwire Patterns](../hotwire-patterns/SKILL.md) — Frontend integration
- [Sidekiq](../sidekiq/SKILL.md) — When you need more than Solid Queue
- [Deploy](../deploy/SKILL.md) — Production deployment
