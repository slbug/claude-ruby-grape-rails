# Error Handling Reference

## Decision Tree

```
Is failure expected in normal operation?
├─ Yes → Return values/exceptions with context
│   ├─ Multiple operations? → Use Result objects or monads
│   └─ Simple validation? → Return false/nil with errors
└─ No (unexpected/bug) → Raise exception
    └─ Let the framework handle recovery
```

## When to Use Each

| Use Exceptions | Use Return Values |
|----------------|-------------------|
| Programming bugs | Expected failures |
| Truly unexpected errors | User input validation |
| Can't recover gracefully | Caller should handle |
| Resource exhaustion | Control flow decisions |

## Exception Hierarchy

Ruby's exception hierarchy:

```
Exception
├── NoMemoryError
├── ScriptError
│   ├── LoadError
│   └── NotImplementedError
├── SecurityError
├── SignalException
├── StandardError          # Rescue THIS for app errors
│   ├── ArgumentError
│   ├── IOError
│   ├── NameError
│   ├── RuntimeError       # Default for `raise`
│   └── TypeError
└── SystemExit
```

**Iron Law**: Never rescue `Exception` — always rescue `StandardError` or specific subclasses.

## Custom Exceptions

```ruby
# Application-specific errors
module Errors
  class ValidationError < StandardError; end
  class NotFoundError < StandardError; end
  class PaymentError < StandardError
    attr_reader :code

    def initialize(message, code: nil)
      super(message)
      @code = code
    end
  end
end

# Usage
raise Errors::PaymentError, "Card declined", code: :card_declined
```

## Result Object Pattern

For operations that can fail expectedly:

```ruby
# Using dry-monads (recommended)
require 'dry/monads'

class CreateOrder
  include Dry::Monads[:result, :do]

  def call(user_id:, product_id:)
    user = yield find_user(user_id)
    product = yield find_product(product_id)
    order = yield create_order(user, product)

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

  def create_order(user, product)
    order = Order.new(user: user, product: product)
    order.save ? Success(order) : Failure(order.errors)
  end
end

# Usage
result = CreateOrder.new.call(user_id: 1, product_id: 2)

result.success? do |order|
  puts "Created: #{order.id}"
end

result.failure? do |error|
  puts "Failed: #{error}"
end
```

## Begin/Rescue/Ensure

```ruby
# Basic rescue
def fetch_data
  response = Net::HTTP.get(url)
  JSON.parse(response)
rescue JSON::ParserError => e
  Rails.logger.warn "Invalid JSON: #{e.message}"
  {}  # Return default
rescue Net::OpenTimeout, Net::ReadTimeout
  Rails.logger.error "Request timeout"
  raise  # Re-raise after logging
end

# Rescue with ensure
def process_file(path)
  file = File.open(path, 'r')
  data = file.read
  parse(data)
rescue Errno::ENOENT
  Rails.logger.error "File not found: #{path}"
  nil
ensure
  file&.close  # Always execute
end

# Rescue with else (rare but valid)
def calculate(values)
  result = risky_math(values)
rescue ArgumentError
  0
else
  cache_result(result)  # Only if no exception
  result
end
```

## Safe Navigation and Validation

```ruby
# DON'T: Silent nil for missing keys
data["key"]["nested"]  # NoMethodError if data["key"] is nil

# DO: Safe navigation
data.dig("key", "nested")  # Returns nil if any key missing
data["key"]&.dig("nested")

# DO: Explicit validation
def process(config)
  raise ArgumentError, "Missing :api_key" unless config[:api_key]

  # Safe to use config[:api_key] now
end

# DO: Hash#fetch for required keys
config.fetch(:api_key) { raise ArgumentError, "api_key required" }
```

## Retry Patterns

```ruby
# Simple retry with backoff
def with_retry(max_attempts: 3)
  attempts = 0

  begin
    attempts += 1
    yield
  rescue Net::ReadTimeout, Net::OpenTimeout => e
    raise if attempts >= max_attempts

    sleep(2 ** attempts)  # Exponential backoff
    retry
  end
end

# Usage
with_retry { api_client.fetch_data }

# Retry with circuit breaker pattern
class CircuitBreaker
  def initialize(threshold: 5, timeout: 60)
    @failure_count = 0
    @threshold = threshold
    @timeout = timeout
    @last_failure_time = nil
  end

  def call
    raise CircuitOpenError if open?

    yield
  rescue StandardError => e
    record_failure
    raise
  end

  private

  def open?
    @failure_count >= @threshold &&
      @last_failure_time &&
      Time.current - @last_failure_time < @timeout
  end

  def record_failure
    @failure_count += 1
    @last_failure_time = Time.current
  end
end
```

## Common Anti-Patterns

```ruby
# DON'T: Rescue Exception (catches everything including SyntaxError)
rescue Exception => e  # WRONG

# DO: Rescue StandardError
rescue StandardError => e  # Correct

# DON'T: Empty rescue
begin
  risky_operation
rescue  # Silent failure - dangerous!
end

# DO: Always handle or re-raise
begin
  risky_operation
rescue => e
  Rails.logger.error "Operation failed: #{e.message}"
  raise  # Re-raise if you can't handle it
end

# DON'T: Use exceptions for flow control
def find_user(id)
  User.find(id)  # Raises if not found
rescue ActiveRecord::RecordNotFound
  nil  # Using exception for normal case
end

# DO: Use proper query methods
def find_user(id)
  User.find_by(id: id)  # Returns nil normally
end
```

## Rails-Specific Patterns

```ruby
# Transaction rollback on error
ActiveRecord::Base.transaction do
  order = Order.create!(params)
  Payment.charge!(order)
rescue Payment::DeclinedError => e
  # Transaction rolls back automatically
  order.update!(status: :payment_failed, error: e.message)
  raise  # Re-raise or handle as needed
end

# Controller error handling
class ApplicationController < ActionController::Base
  rescue_from ActiveRecord::RecordNotFound, with: :not_found
  rescue_from Errors::Unauthorized, with: :unauthorized

  private

  def not_found
    render json: { error: "Not found" }, status: :not_found
  end

  def unauthorized
    render json: { error: "Unauthorized" }, status: :unauthorized
  end
end
```
