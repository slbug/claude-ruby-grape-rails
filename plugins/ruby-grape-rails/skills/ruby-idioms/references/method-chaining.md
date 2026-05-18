# Method Chaining and Error Handling

## When to Chain

| Use case | Pattern |
|---|---|
| Data transformation pipeline | `.then { ... }` |
| ActiveRecord query building | `.where(...).order(...).limit(...)` |
| Object construction with side effects | `.tap { ... }` |
| Lazy enumeration over large input | `.lazy.map.select.first(N).force` |

```ruby
params.dig("user", "email")&.strip&.downcase

User
  .where(active: true)
  .where(role: roles)
  .order(created_at: :desc)
  .limit(10)
  .to_a

User.new
  .tap { |u| u.assign_attributes(params) }
  .tap { |u| u.status = :pending }
  .tap(&:valid?)

(1..1000)
  .lazy
  .map { |i| expensive_operation(i) }
  .select { |x| valid?(x) }
  .first(10)
  .force

data
  .then { |d| JSON.parse(d, symbolize_names: true) }
  .then { |d| validate_user_data(d) }
  .then { |d| User.new(d) }
  .then(&:save!)
```

Ruby 3.4+ `it` keyword keeps single-arg block bodies short:

```ruby
data
  .then { JSON.parse(it, symbolize_names: true) }
  .then { validate_user_data(it) }
  .then { User.new(it) }
```

## When NOT to Chain

| Reject | Reason |
|---|---|
| Single method call | No pipeline value |
| Mid-chain conditional with `if/else` | Extract to named method |
| Chain receiver is a method call, not data | Re-anchor on the data |

```ruby
data.transform.then { handle_condition(it, condition) }

def handle_condition(x, condition)
  condition ? a(x) : b(x)
end
```

Anchor on the data:

```ruby
User.find(id).tap(&:process)
```

Reject `get_user(id).process` — the chain reads from a verb, not a noun.

## Error Handling

### `rescue` with explicit error class

```ruby
def create_order(params)
  user = User.find(params[:user_id])
  product = Product.find(params[:product_id])
  check_inventory!(product)
  order = Order.create!(user: user, product: product)
  { success: true, order: order }
rescue ActiveRecord::RecordNotFound => e
  { success: false, error: :not_found, message: e.message }
rescue InventoryError
  { success: false, error: :out_of_stock }
end
```

Iron Law 18: never `rescue Exception` (catches `SystemExit` /
`SignalException`). Bare `rescue` defaults to `StandardError` and is
technically safe; explicit class naming (`rescue SpecificError =>`)
is a style preference for clarity, not a Law 18 violation.

### Result-object early return

```ruby
def update_post(user, post_id, params)
  post = Post.find_by(id: post_id)
  return Result.failure(:not_found) unless post
  return Result.failure(:unauthorized) unless user.can_update?(post)

  if post.update(params)
    Result.success(post)
  else
    Result.failure(:validation_error, post.errors)
  end
end
```

### dry-monads `do` notation

```ruby
require 'dry/monads'

class OrderService
  include Dry::Monads[:result, :do]

  def create(params)
    user    = yield find_user(params[:user_id])
    product = yield find_product(params[:product_id])
    yield check_inventory(product)
    order   = yield create_order(user, product, params)
    Success(order)
  end

  private

  def find_user(id)
    user = User.find_by(id: id)
    user ? Success(user) : Failure(:user_not_found)
  end

  def find_product(id)
    product = Product.find_by(id: id)
    product ? Success(product) : Failure(:product_not_found)
  end

  def check_inventory(product)
    product.in_stock? ? Success() : Failure(:out_of_stock)
  end

  def create_order(user, product, params)
    order = Order.new(user: user, product: product, **params)
    order.save ? Success(order) : Failure(order.errors)
  end
end
```

### Pattern matching for result dispatch (Ruby 3.0+)

```ruby
def handle_result(result)
  case result
  in { success: true, data: { user: User => user } }
    process_user(user)
  in { success: false, error: :not_found }
    render_not_found
  in { success: false, error: :unauthorized }
    render_unauthorized
  else
    render_error
  end
end

def process_response(response)
  case response
  in { status: 200..299, body: String => body }
    JSON.parse(body)
  in { status: 404 }
    raise NotFoundError
  in { status: code } if code >= 500
    raise ServerError
  end
end
```

### Early returns vs exceptions

Use early returns for validation; use exceptions for genuinely
exceptional paths (network failure, transactional rollback).

```ruby
def process_payment(order)
  return failure(:order_not_found) unless order
  return failure(:already_paid) if order.paid?
  return failure(:invalid_amount) unless order.amount.positive?

  charge = create_charge(order)
  return failure(:charge_failed) unless charge

  order.mark_as_paid!(charge)
  success(order)
end

def create_charge(order)
  Stripe::Charge.create(
    amount: order.amount_cents,
    currency: 'usd',
    customer: order.user.stripe_customer_id
  )
rescue Stripe::CardError => e
  Rails.logger.error "Payment failed: #{e.message}"
  raise PaymentError, e.message
end
```

### Multiple operations

```ruby
def process_orders(orders)
  orders.each_with_object({ processed: [], failed: [] }) do |order, acc|
    if process(order)
      acc[:processed] << order
    else
      acc[:failed] << order
    end
  end
end

def fetch_users(ids)
  ids.filter_map do |id|
    user = User.find_by(id: id)
    user if user&.active?
  end
end

def process_large_dataset
  User
    .where(active: true)
    .lazy
    .select { |u| u.orders_count > 5 }
    .map { |u| format_user(u) }
    .first(100)
end
```

## Production Examples

### Service object

```ruby
class DealService
  def self.update_deal(broker, deal_id, params)
    deal = Deal.find_by(id: deal_id)
    return Result.failure(:not_found) unless deal
    return Result.failure(:unauthorized) unless broker.can_update?(deal)

    deal.update!(params)
    broadcast_update(deal)
    Result.success(deal)
  rescue ActiveRecord::RecordInvalid => e
    Result.failure(:validation_error, e.record.errors)
  end
end
```

### Query builder

```ruby
class ArticleQuery
  def self.for_profile(profile_id, opts = {})
    Article
      .where(profile_id: profile_id)
      .then { |scope| filter_by_search(scope, opts[:search]) }
      .then { |scope| filter_by_status(scope, opts[:status]) }
      .then { |scope| filter_by_rating(scope, opts[:rating]) }
      .then { |scope| apply_sort(scope, opts[:sort_by], opts[:sort_order]) }
      .then { |scope| maybe_limit(scope, opts[:limit]) }
  end

  def self.filter_by_search(scope, term)
    term.present? ? scope.where("title ILIKE ?", "%#{term}%") : scope
  end
end
```

### Model with optimistic-lock retry

```ruby
class Guest < ApplicationRecord
  def confirm!(params)
    with_lock do
      assign_attributes(params)
      self.confirmed_at = Time.current
      save!
      update_attendees!(params[:attendees_count])
    end
  rescue ActiveRecord::StaleObjectError
    retry
  end
end
```

### Feature gate via early returns

```ruby
class FeatureChecker
  def self.check_access(user, feature)
    return Result.failure(:billing_disabled) unless billing_enforced?

    subscription = user.active_subscription
    return Result.failure(:no_subscription) unless subscription
    return Result.failure(:feature_not_included) unless subscription.includes?(feature)

    Result.success
  end
end
```

## Pattern Decision Table

| Pattern | Use | Avoid |
|---|---|---|
| Method chain | Transformation, query build | Single call, complex branching mid-chain |
| `.then` / `it` | Pipeline ops (Ruby 2.5+ / 3.4+) | One-liners |
| `rescue` | Exceptional cases | Control flow |
| Early return | Validation, guards | Deeply nested logic |
| `Result` object | Multiple failure modes | Boolean success |
| Pattern matching | Structured data dispatch (Ruby 3.0+) | Simple conditional |

## Reject Patterns

### Stepwise temporary variables for a transform

Reject:

```ruby
result1 = function1(data)
result2 = function2(result1)
result3 = function3(result2)
final   = function4(result3)
```

Use a chain:

```ruby
final = data
  .then { function1(it) }
  .then { function2(it) }
  .then { function3(it) }
  .then { function4(it) }
```

### Deeply nested conditionals

Reject:

```ruby
user = User.find_by(id: user_id)
if user
  subscription = user.subscription
  if subscription
    if subscription.active?
      if subscription.includes?(feature)
        :ok
      else
        :feature_not_included
      end
    else
      :subscription_inactive
    end
  else
    :no_subscription
  end
else
  :user_not_found
end
```

Flatten with early returns:

```ruby
def check_access(user_id, feature)
  user = User.find_by(id: user_id)
  return :user_not_found unless user

  subscription = user.subscription
  return :no_subscription          unless subscription
  return :subscription_inactive    unless subscription.active?
  return :feature_not_included     unless subscription.includes?(feature)

  :ok
end
```

Or pattern match:

```ruby
case { user: User.find_by(id: user_id), feature: feature }
in { user: nil }
  :user_not_found
in { user: u, subscription: nil }
  :no_subscription
in { user: u, subscription: s } unless s.active?
  :subscription_inactive
in { user: u, subscription: s } unless s.includes?(feature)
  :feature_not_included
else
  :ok
end
```
