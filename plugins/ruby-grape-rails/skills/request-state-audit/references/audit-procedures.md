# Request State Audit Reference

Detailed procedures and patterns for auditing Rails request state.

## Audit Categories

### 1. CurrentAttributes Usage

**Modern Rails Behavior:** `CurrentAttributes` automatically resets before and after each request. Manual reset is not required for normal controller usage.

**Audit Focus:** Jobs, threads, and async contexts where automatic reset does not apply.

**Patterns to Check:**

```ruby
# ✅ GOOD: Normal request usage (Rails auto-resets)
class ApplicationController < ActionController::Base
  before_action :set_current_user

  private

  def set_current_user
    Current.user = current_user  # Safe - Rails resets automatically
  end
end

# ❌ BAD: Using Current in job without explicit context
class OrderJob < ApplicationJob
  def perform(order_id)
    order = Order.find(order_id)
    # Current.user may be stale or nil here!
    OrderMailer.confirmation(order, Current.user).deliver_later
  end
end

# ✅ GOOD: Pass context explicitly to jobs
class OrderJob < ApplicationJob
  def perform(order_id, user_id)
    order = Order.find(order_id)
    user = User.find(user_id)
    OrderMailer.confirmation(order, user).deliver_later
  end
end

# ✅ GOOD: Or use Current.set for non-request contexts
class OrderJob < ApplicationJob
  def perform(order_id, user_id)
    user = User.find(user_id)
    Current.set(user: user) do
      order = Order.find(order_id)
      OrderMailer.confirmation(order).deliver_later
    end
  end
end
```

**External Collaborators:**

If `Current` interacts with external state (like `Time.zone`), register a reset callback:

```ruby
class Current < ActiveSupport::CurrentAttributes
  resets { Time.zone = nil }
end
```

**Checklist:**

- [ ] Jobs don't assume `Current` context from requests (pass args or use `Current.set`)
- [ ] Custom threads/fibers don't access `Current` without explicit context
- [ ] External collaborators registered via `resets { ... }` if needed
- [ ] Not over-stuffing controller-specific values into global Current

---

### 2. Session/Cookie Bloat

**Problem:** Sessions grow unbounded, causing performance issues.

**Patterns to Check:**

```ruby
# ❌ BAD: Storing large objects in session
session[:user] = user.attributes  # Could be huge!
session[:cart] = cart.items       # Unbounded growth

# ✅ GOOD: Store IDs only
session[:user_id] = user.id
session[:cart_id] = cart.id
```

**Checklist:**

- [ ] Session size < 4KB (cookie storage limit)
- [ ] No ActiveRecord objects in session
- [ ] Flash messages cleared properly
- [ ] Session keys have expiration/TTL

---

### 3. Redis Key Organization & TTL

**Problem:** Keys without environment separation collide between environments. Keys without TTL fill up Redis.

**Patterns to Check:**

```ruby
# ❌ BAD: No environment separation, no TTL
Rails.cache.write("user:#{user.id}", data)
Redis.current.set("session:#{session_id}", data)

# ✅ GOOD: Environment prefix with TTL (for shared Redis)
Rails.cache.write("#{Rails.env}:user:#{user.id}", data, expires_in: 1.hour)
Redis.current.setex("#{Rails.env}:session:#{session_id}", 3600, data)
```

**Best Practice:** Use separate Redis instances per environment (production, staging, dev) rather than sharing one instance with key prefixes. Sidekiq recommends separate instances for job queues.

**Checklist:**

- [ ] Separate Redis instances per environment (preferred) OR all keys include environment prefix
- [ ] All cache writes have `expires_in`
- [ ] Redis memory usage monitored
- [ ] Sidekiq uses dedicated Redis instance (not shared with cache/sessions)

---

### 4. Turbo Stream Timing

**Problem:** Broadcasting Turbo streams from `after_create` (not `_commit`) causes race conditions because the record may not be visible to other connections yet.

**Patterns to Check:**

```ruby
# ❌ BAD: Broadcasting before transaction commit
class Post < ApplicationRecord
  after_create -> {
    broadcast_prepend_to "posts"  # May run before record is visible to other connections!
  }
end

# ✅ GOOD: Broadcast after transaction is committed
class Post < ApplicationRecord
  after_create_commit -> {
    broadcast_prepend_to "posts"
  }
end
```

**Checklist:**

- [ ] All `broadcast_*` calls in `after_commit` callbacks
- [ ] No DB queries in stream view templates
- [ ] Stream data pre-computed before broadcast

---

### 5. Duplicated Sources of Truth

**Problem:** Same data stored in multiple places, gets out of sync.

**Patterns to Check:**

```ruby
# ❌ BAD: Denormalized without sync
class Order < ApplicationRecord
  after_save :update_user_stats
  
  def update_user_stats
    user.update(total_orders: user.orders.count)
  end
end

# ✅ GOOD: Single source of truth, computed when needed
class User < ApplicationRecord
  def total_orders
    orders.count  # Always accurate
  end
end
```

**Checklist:**

- [ ] Counters have clear invalidation strategy
- [ ] No manual cache invalidation scattered in callbacks
- [ ] Materialized views refreshed properly

---

## Remediation Patterns

### CurrentAttributes in Jobs

```ruby
# ❌ BAD: Assuming Current context in job
class OrderJob < ApplicationJob
  def perform(order_id)
    order = Order.find(order_id)
    OrderMailer.confirmation(order, Current.user).deliver_later
  end
end

# ✅ GOOD: Explicit context via Current.set
class OrderJob < ApplicationJob
  def perform(order_id, user_id)
    user = User.find(user_id)
    Current.set(user: user) do
      order = Order.find(order_id)
      OrderMailer.confirmation(order).deliver_later
    end
  end
end

# ✅ GOOD: Or pass values explicitly (preferred)
class OrderJob < ApplicationJob
  def perform(order_id, user_id)
    order = Order.find(order_id)
    user = User.find(user_id)
    OrderMailer.confirmation(order, user).deliver_later
  end
end
```

### CurrentAttributes External Collaborators

If `Current` interacts with external state, register a reset callback:

```ruby
class Current < ActiveSupport::CurrentAttributes
  attribute :user, :account
  
  # Reset external collaborators when Current resets
  resets { Time.zone = nil }
end
```

### Redis Configuration

```ruby
# config/initializers/redis.rb
# Use separate Redis instances per environment (recommended)
Redis.current = Redis.new(url: ENV['REDIS_URL'])

# For cache store
config.cache_store = :redis_cache_store, {
  url: ENV['REDIS_CACHE_URL'],  # Separate from job queue Redis
  expires_in: 1.hour
}
```

**Note:** Sidekiq recommends separate Redis instances over namespaces. Configure `REDIS_URL` for Sidekiq and `REDIS_CACHE_URL` for Rails cache.

### Session Cleanup Rake Task

```ruby
# lib/tasks/session_cleanup.rake
namespace :sessions do
  desc "Clean up old session data"
  task cleanup: :environment do
    # If using Redis for sessions
    redis = Redis.current
    keys = redis.keys("#{Rails.env}:session:*")
    keys.each do |key|
      redis.expire(key, 2.weeks.to_i) unless redis.ttl(key) > 0
    end
  end
end
```

---

## Tools for Investigation

### Check Redis Key Stats

```bash
# List keys by prefix
redis-cli --scan --pattern "*:user:*" | wc -l

# Find keys without TTL
redis-cli --scan | while read key; do ttl=$(redis-cli ttl "$key"); if [ "$ttl" -lt 0 ]; then echo "$key (TTL: $ttl)"; fi; done

# Memory usage by prefix
redis-cli --bigkeys
```

### Monitor CurrentAttributes

```ruby
# Add to ApplicationController for debugging
before_action :debug_current

def debug_current
  Rails.logger.info "Current.user before: #{Current.user.inspect}"
  yield
ensure
  Rails.logger.info "Current.user after: #{Current.user.inspect}"
end
```

### Session Size Audit

```ruby
# rails console
session_data = Session.all.pluck(:data)
session_data.map { |d| d.to_s.bytesize }.max
session_data.map { |d| d.to_s.bytesize }.sum
```
