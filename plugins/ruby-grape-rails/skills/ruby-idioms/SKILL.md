---
name: ruby-idioms
description: Core Ruby 3.4+/4.0-ready idioms for application code. Value objects, service objects, error handling, adapters. Load for plain Ruby objects and service boundaries.
user-invocable: false
effort: medium
---
# Ruby Idioms

## Iron Laws

1. Prefer simple objects over metaprogramming
2. Raise exceptions for failures; return values for expected branches
3. Keep mutation narrow and obvious
4. Wrap third-party APIs behind project-owned adapters
5. Avoid global state and hidden thread-local coupling
6. Consider `it` for simple single-argument blocks when clarity permits
7. Prefer pattern matching for complex data destructuring
8. Enable YJIT in production (Ruby 3.2+; Rails 7.2+ enables by default on Ruby 3.3+)

## Ruby 3.4+ Features

### The `it` Keyword

```ruby
# Before
users.map { |user| user.name }
orders.select { |o| o.completed? }

# After (Ruby 3.4+)
users.map { it.name }
orders.select { it.completed? }
```

**Use when:** Single argument, 1-2 method calls, no nesting  
**Avoid when:** Multiple args, complex logic, nested blocks

### Pattern Matching

```ruby
case response
in { status: 200, body: { data: items } }
  items
in { status: 404 }
  raise NotFoundError
in { status: code, body: { error: msg } }
  raise ApiError.new("#{code}: #{msg}")
end
```

**Use for:** Complex data structures, state machines, event handling  
**Avoid for:** Simple cases (use if/when instead)

### YJIT (Ruby 3.2+) — Current Recommendation

YJIT is the production-ready JIT compiler for Ruby 3.x:

```ruby
# Check if YJIT is enabled
RubyVM::YJIT.enabled?  # => true

# Enable in production:
# Environment variable: RUBY_YJIT_ENABLE=1
# Or in code before app loads: RubyVM::YJIT.enable
```

**Benefits:** 15-30% performance improvement for Rails apps

**Status:**

- Bare Ruby: Not enabled by default; enable via `RUBY_YJIT_ENABLE=1` or `RubyVM::YJIT.enable`
- Rails 7.2+: Enabled by default when running on Ruby 3.3+

### ZJIT (Ruby 4.0+) — Experimental

ZJIT is the next-generation JIT compiler in Ruby 4.0:

```ruby
# Verify ZJIT is enabled (Ruby 4.0+)
puts RubyVM::ZJIT.enabled?  # => true

# Enable: ruby --zjit (CLI) or RubyVM::ZJIT.enable (runtime)
```

**Status:** Experimental/not recommended for production; YJIT remains the recommended JIT for Ruby 3.2-4.0  

## Core Patterns

### Value Objects

```ruby
class Money
  include Comparable
  attr_reader :cents, :currency
  
  def initialize(cents, currency = "USD")
    @cents = cents
    @currency = currency
    freeze
  end
  
  def <=>(other)
    return nil unless currency == other.currency
    cents <=> other.cents
  end
  
  def hash = [cents, currency].hash
  alias_method :eql?, :==
  
  def +(other)
    raise CurrencyMismatch unless currency == other.currency
    Money.new(cents + other.cents, currency)
  end
end
```

### Result Objects

```ruby
class Result
  def self.success(value) = new(value: value)
  def self.failure(error) = new(error: error)
  
  attr_reader :value, :error
  def initialize(value: nil, error: nil)
    @value = value
    @error = error
    freeze
  end
  
  def success? = error.nil?
  def failure? = !success?
  def bind = success? ? yield(value) : self
end

# Usage
result = process_payment
result.success? ? render(json: result.value) : render_error(result.error)
```

### Service Objects

```ruby
class CreateOrder
  def initialize(
    inventory_checker: InventoryChecker.new,
    payment_processor: PaymentProcessor.new
  )
    @inventory_checker = inventory_checker
    @payment_processor = payment_processor
  end
  
  def call(user:, items:, payment_method:)
    check_inventory!(items)
    order = Order.create!(user: user, items: items)
    process_payment!(order, payment_method)
    Result.success(order)
  rescue InsufficientInventory => e
    Result.failure("Out of stock: #{e.item_name}")
  rescue PaymentError => e
    order.cancel!
    Result.failure("Payment failed: #{e.message}")
  end
  
  private
  
  attr_reader :inventory_checker, :payment_processor
  
  def check_inventory!(items) = items.each { inventory_checker.check!(it) }
  def process_payment!(order, pm) = payment_processor.charge!(order.total, pm)
end
```

### Adapter Pattern

```ruby
class StripeAdapter
  def initialize(api_key: ENV['STRIPE_API_KEY'])
    @client = Stripe::StripeClient.new(api_key)
  end
  
  def create_charge(amount:, currency:, source:)
    result = client.request do
      Stripe::Charge.create(
        amount: amount.cents,
        currency: currency.downcase,
        source: source
      )
    end
    
    ChargeResult.new(
      id: result.id,
      amount: Money.new(result.amount, result.currency.upcase),
      status: result.status
    )
  rescue Stripe::CardError => e
    raise PaymentError, e.message
  end
  
  private
  
  attr_reader :client
end
```

### Error Handling

```ruby
module MyApp
  class Error < StandardError; end
  class ValidationError < Error
    attr_reader :field
    def initialize(message, field: nil)
      super(message)
      @field = field
    end
  end
  class NotFoundError < Error; end
  class ExternalServiceError < Error; end
  class TimeoutError < ExternalServiceError; end
end

# Retry with exponential backoff
def with_retry(max_attempts: 3, base_delay: 1)
  attempts = 0
  begin
    attempts += 1
    yield
  rescue TimeoutError => e
    raise if attempts >= max_attempts
    sleep(base_delay * (2 ** (attempts - 1)))
    retry
  end
end
```

## Performance Tips

```ruby
# Use symbols over strings for internal identifiers
# Ruby 4.0 makes frozen string literals the default (no longer optional)
# Use String#<< over String#+ for building strings
# Use Hash#fetch for defaults
# Use Set for O(1) membership testing
# Use safe navigation (&.) judiciously
```

## Anti-patterns

**Don't:**

- Use class variables (`@@count`) — use instance variables on class instead
- Monkey patch core classes — use refinements
- Rescue Exception — rescue StandardError or specific types
- Use eval with user input — use JSON.parse or YAML.safe_load

## References

- `references/pattern-matching.md` — Advanced pattern matching patterns
- `references/data-transformations.md` — Functional pipelines and transformations
- `references/enumerable-patterns.md` — Lazy enumeration and batching
- `references/testing-patterns.md` — RSpec patterns with modern Ruby
- `references/ruby-4-migration.md` — Ruby 4.0 upgrade guide
