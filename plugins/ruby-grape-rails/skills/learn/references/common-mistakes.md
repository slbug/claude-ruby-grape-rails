# Common Mistakes — Reference

> **READ-ONLY**: This file ships with the plugin. Do NOT edit it
> at runtime — changes to cached plugin files are lost on update.
> To capture new lessons, use `/rb:learn` which writes to
> project CLAUDE.md, auto-memory, or `.claude/solutions/`.

Common Ruby/Rails/Grape mistakes and their fixes. `/rb:learn` checks
this file during duplicate detection (Step 2). If the lesson is already
here, skip it — tell the user and stop.

Format:

- **Mistake**: What went wrong
- **Pattern**: Do NOT [bad] - instead [good]
- **Example**: Code showing before/after

---

## Active Record

### String vs Atom Keys

**Mistake**: Using string keys for internal data, atom keys for external

**Pattern**: Do NOT use `map["key"]` for internal structs - instead use `map.key` or pattern match

**Example**:

```ruby
# Bad - external data pattern on internal struct
user["email"]

# Good - method access for internal data
user.email
email = user.email
```

### Missing Preload

**Mistake**: Accessing association without preloading

**Pattern**: Do NOT access `record.association` without eager loading - instead use `.includes()` or preload in query

**Example**:

```ruby
# Bad - causes ActiveRecord::AssociationNotLoaded
user = User.find(id)
user.posts  # Boom!

# Good - explicit includes
user = User.includes(:posts).find(id)
user.posts  # Works
```

---

## Hotwire/Turbo

### Blocking Mount

**Mistake**: Slow operations in controller action blocking page render

**Pattern**: Do NOT do slow work in controller - instead use Turbo Frames or background jobs

**Example**:

```ruby
# Bad - blocks page render
class DashboardController < ApplicationController
  def index
    @slow_data = SlowAPI.fetch  # User waits...
  end
end

# Good - use Turbo Frame for lazy loading
<%= turbo_frame_tag "dashboard_data", src: dashboard_data_path do %>
  Loading...
<% end %>
```

### Missing Async Handling in Tests

**Mistake**: Testing async operations without waiting for completion

**Pattern**: Do NOT assert on async data immediately - instead use `sleep` with small timeout or polling

**Example**:

```ruby
# Bad - async not completed yet
visit dashboard_path
assert_text "Data"  # Fails!

# Good - wait for async
visit dashboard_path
sleep 0.1
assert_text "Data"  # Works
```

---

## Background Jobs

### Unnecessary Complex State Management

**Mistake**: Creating complex stateful services for simple computation

**Pattern**: Do NOT use stateful services for code organization - instead use POROs (Plain Old Ruby Objects)

**Example**:

```ruby
# Bad - over-engineering with stateful service
class CalculatorService
  def initialize(a, b)
    @a = a
    @b = b
  end
  
  def add
    @a + @b
  end
end

CalculatorService.new(1, 2).add

# Good - just a function
module Calculator
  extend self
  
  def add(a, b)
    a + b
  end
end

Calculator.add(1, 2)
```

---

## Testing

### Sleep for Timing

**Mistake**: Using sleep to wait for async operations

**Pattern**: Do NOT use `sleep` in tests - instead use `assert_difference` or `travel_to` helpers

**Example**:

```ruby
# Bad - flaky, slow
test "processes message" do
  send_message
  sleep 0.1
  assert processed?
end

# Good - deterministic
test "processes message" do
  assert_difference -> { Message.count }, 1 do
    send_message
  end
end
```

### create() in Factory Definition

**Mistake**: Using create() inside factory, creating DB records even on build()

**Pattern**: Do NOT use `create` in factory definitions - instead use `build` or associations

**Example**:

```ruby
# Bad - creates user even on build(:post)
FactoryBot.define do
  factory :post do
    author { create(:user) }
  end
end

# Good - lazy association
FactoryBot.define do
  factory :post do
    association :author, factory: :user
  end
end
```

---

## Rails

### Business Logic in Controller

**Mistake**: Complex logic in controller actions

**Pattern**: Do NOT put business logic in controllers - instead delegate to service/context classes

**Example**:

```ruby
# Bad - logic in controller
class UsersController < ApplicationController
  def create
    params[:user][:role] = 'member'
    if valid_email?(params[:user][:email])
      # 20 more lines...
    end
  end
end

# Good - delegate to service
class UsersController < ApplicationController
  def create
    result = UserRegistration.call(params[:user])
    
    if result.success?
      redirect_to user_path(result.user)
    else
      render :new, status: :unprocessable_entity
    end
  end
end
```
