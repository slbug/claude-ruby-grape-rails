# Pattern Matching Reference

Ruby 3.0+ introduced pattern matching with `case/in`. Ruby 3.4+ expands this with `it` implicit block parameters and additional pattern types.

## Basic Case/In Matching

```ruby
# Match against data structures
data = { status: :success, user: { name: "Alice", id: 1 } }

case data
in { status: :success, user: { name:, id: } }
  puts "User #{name} (ID: #{id})"
in { status: :error, message: }
  puts "Error: #{message}"
in { status: }
  puts "Unknown status: #{status}"
else
  puts "Unexpected format"
end
```

## Array Patterns

```ruby
# Basic array destructuring
result = [200, { data: "value" }]

case result
in [200, payload]
  puts "Success: #{payload}"
in [404, _]
  puts "Not found"
in [code, _] if code >= 500
  puts "Server error: #{code}"
else
  puts "Unknown response"
end

# With array splat
items = [1, 2, 3, 4, 5]

case items
in [first, *middle, last]
  puts "First: #{first}, Last: #{last}, Middle: #{middle}"
in []
  puts "Empty array"
end

# Find patterns (Ruby 3.4+)
case items
in [*, 3, *]
  puts "Contains 3"
end
```

## Hash Patterns

```ruby
# Basic hash matching
user = { name: "Bob", age: 30, email: "bob@example.com" }

case user
in { name:, age: 30 }
  puts "#{name} is 30"
in { name:, email: }
  puts "#{name} has email #{email}"
end

# Hash splat for partial matching
case user
in { name:, **rest }
  puts "Name: #{name}"
  puts "Other fields: #{rest.keys}"
end

# Empty hash pattern
config = {}

case config
in {}
  puts "Empty config"
end
```

## Value Patterns and Guards

```ruby
# Pin operator (^) - match against existing values
expected_status = :success

case response
in { status: ^expected_status }
  puts "Got expected status"
in { status: }
  puts "Got #{status}, expected #{expected_status}"
end

# Guard clauses
data = { type: :premium, credits: 100 }

case data
in { type: :premium, credits: } if credits > 50
  puts "Premium user with #{credits} credits"
in { type: :premium, credits: }
  puts "Premium user with low credits: #{credits}"
in { type: :basic }
  puts "Basic user"
end
```

## Alternative Patterns

```ruby
# Match multiple possibilities
code = :not_found

case code
in :ok | :created | :accepted
  puts "Success"
in :not_found | :gone
  puts "Not found"
in :error | :timeout
  puts "Failure"
end
```

## As Patterns

```ruby
# Capture the entire matched value
data = { user: { name: "Alice", role: :admin } }

case data
in { user: { name:, role: :admin } } => admin_data
  puts "Admin: #{name}"
  puts "Full data: #{admin_data}"
end
```

## Object Patterns

```ruby
# Match against custom objects
class Point
  attr_reader :x, :y

  def initialize(x, y)
    @x = x
    @y = y
  end

  def deconstruct_keys(keys)
    { x: @x, y: @y }
  end
end

point = Point.new(10, 20)

case point
in Point(x: 0, y: 0)
  puts "Origin"
in Point(x:, y:)
  puts "Point at (#{x}, #{y})"
end

# Array deconstruction
class Range
  def deconstruct
    [min, max]
  end
end

range = (1..10)

case range
in [0, *]
  puts "Starts at 0"
in [min, max]
  puts "Range #{min}..#{max}"
end
```

## Practical Examples

```ruby
# API response handling
def handle_response(response)
  case response
  in { status: 200..299, body: { data: } }
    Result.success(data)
  in { status: 401, body: { error: message } }
    Result.failure(:unauthorized, message)
  in { status: 404 }
    Result.failure(:not_found)
  in { status: 500..599 }
    Result.failure(:server_error)
  else
    Result.failure(:unknown, response)
  end
end

# Event handling
def handle_event(event)
  case event
  in { type: "user.created", data: { id:, email: } }
    UserMailer.welcome_email(email).deliver_later
  in { type: "order.completed", data: { order_id:, total: } }
    Order.complete(order_id)
    Analytics.track("order_completed", value: total)
  in { type: }
    Rails.logger.warn "Unhandled event type: #{type}"
  end
end

# Configuration validation
def validate_config(config)
  case config
  in { database: { host:, port: 5432.., username:, password: } }
    :valid
  in { database: { port: } } unless (5432..).include?(port)
    raise "Invalid port: #{port}"
  else
    raise "Missing required database configuration"
  end
end
```

## Pattern Matching vs Other Approaches

```ruby
# Traditional approach
def process(data)
  if data.is_a?(Hash) && data[:status] == :success
    user = data[:user]
    if user.is_a?(Hash)
      name = user[:name]
      puts name if name
    end
  end
end

# Pattern matching approach
def process(data)
  case data
  in { status: :success, user: { name: } }
    puts name
  end
end
```

## Ruby 3.4+ `it` Parameter

```ruby
# Before Ruby 3.4
[1, 2, 3].map { |n| n * 2 }

# Ruby 3.4 with numbered parameters
[1, 2, 3].map { _1 * 2 }

# Ruby 3.4 with `it`
[1, 2, 3].map { it * 2 }

# In pattern matching (when using blocks)
users.map do
  case it
  in { admin: true, name: }
    "Admin: #{name}"
  in { name: }
    "User: #{name}"
  end
end
```

## Best Practices

1. **Use exhaustive matching**: Always include `else` for unexpected cases
2. **Pin values when needed**: Use `^variable` to match against existing values
3. **Keep patterns simple**: Complex patterns are harder to read than explicit code
4. **Prefer destructuring**: Extract values directly in the pattern
5. **Use guards sparingly**: Complex guards make patterns hard to follow
