# Ruby 3.4/4.0 Features Reference

> **Official changelog**: <https://github.com/ruby/ruby/blob/master/NEWS.md>
> **Ruby guides**: <https://guides.rubyonrails.org/>

## Pattern Matching (3.0+ Enhanced)

```ruby
# Case/in pattern matching
case data
in { status: 200, body: String => body }
  puts "Success: #{body}"
in { status: 404 }
  puts "Not found"
in { status: code }
  puts "Error: #{code}"
end

# Array pattern matching
case [1, 2, 3]
in [a, b, c]
  puts "Got #{a}, #{b}, #{c}"
end

# Find patterns (3.2+)
case [1, 2, 3, 4, 5]
in [*, 3, *rest]
  puts "Found 3, rest: #{rest.inspect}"
end

# Hash pattern with rest (3.2+)
case { a: 1, b: 2, c: 3 }
in { a: Integer, **rest }
  puts "a is integer, rest: #{rest.inspect}"
end
```

## Endless Method Definition (3.0+)

```ruby
# Single-line method definition
def square(x) = x * x

def greet(name) = puts "Hello, #{name}!"

# With default args
def greet(name = "World") = "Hello, #{name}!"
```

## Numbered Parameters (2.7+) and "it" Keyword (3.4+)

Ruby 3.4 introduces the `it` keyword for implicit block parameters, providing a cleaner alternative to numbered params.

### Using "it" (Ruby 3.4+)

```ruby
# Single implicit param with "it"
[1, 2, 3].map { it * 2 }
# => [2, 4, 6]

users.map { it.name }
# => ["Alice", "Bob", "Carol"]

items.select { it.price > 10 }
# Select items with price > 10

# With method chaining
posts.map { it.title.upcase }

# In sort_by
products.sort_by { it.price }
```

### Using Numbered Params (Ruby 2.7+)

```ruby
# Implicit block params with _1, _2, etc.
[1, 2, 3].map { _1 * 2 }
# => [2, 4, 6]

# Multiple params with _1, _2
[[1, 2], [3, 4]].map { _1 + _2 }
# => [3, 7]

# Hash.each with _1 (key) and _2 (value)
{ a: 1, b: 2 }.each { puts "#{_1}: #{_2}" }
```

### When to Use What

| Style | Best For | Example |
|-------|----------|---------|
| `it` | Single param, simple expression | `users.map { it.name }` |
| `_1` | Backward compatibility, multiple params | `[[1, 2]].map { _1 + _2 }` |
| Named | Complex logic, clarity needed | `users.map { \|u\| u.name.upcase }` |

### Guidelines

```ruby
# ✅ Good: Simple transformation with "it" (3.4+)
users.map { it.name }
posts.map { it.title }

# ✅ Good: Simple transformation with _1 (2.7+)
users.map { _1.name }

# ✅ Good: Multiple params need numbered params
pairs.map { _1 + _2 }  # "it" can't do this

# ✅ Good: Complex logic needs named params
users.map do |user|
  name = user.name.upcase
  email = user.email.downcase
  "#{name} <#{email}>"
end

# ❌ Bad: Don't mix "it" with named params
users.map { |u| it.name }  # Syntax error!

# ❌ Bad: Avoid in nested blocks
users.map { posts.map { it.title } }  # Which "it"?

# ✅ Good: Named params for nested blocks
users.map { |u| u.posts.map { |p| p.title } }
```

## Argument Forwarding (2.7+ Enhanced)

```ruby
# Forward all arguments with ...
def wrapper(...)
  target(...)
end

# With leading args
def log_and_call(msg, ...)
  puts msg
  target(...)
end

# Block forwarding
def with_block(&)
  items.each(&)
end
```

## Fiber Scheduler (3.0+) - Async/Await

```ruby
# Using Async gem with Fiber scheduler
require 'async'

Async do
  # Concurrent operations within a reactor
  task1 = Async { fetch_data_from_api }
  task2 = Async { read_from_database }
  
  # Wait for both
  data = task1.wait
  db_result = task2.wait
end

# Rails async handling
class AsyncController < ApplicationController
  def index
    Async do
      @data = fetch_data
      render json: @data
    end
  end
end
```

## Ractor (3.0+) - True Parallelism

```ruby
# Experimental actor-model concurrency
ractor = Ractor.new do
  loop do
    msg = Ractor.receive
    puts "Received: #{msg}"
  end
end

ractor.send("Hello from main")

# Parallel map with Ractors
def parallel_map(array, &block)
  ractors = array.map do |item|
    Ractor.new(item, &block)
  end
  
  ractors.map(&:take)
end

# Note: Ractors have strict isolation - share nothing
```

## Data Classes (3.2+ Experimental)

```ruby
# Immutable value objects
class Point < Data.define(:x, :y)
  def distance_from_origin
    Math.sqrt(x**2 + y**2)
  end
end

p1 = Point.new(3, 4)
p2 = Point.new(3, 4)

p1 == p2        # => true
p1.hash == p2.hash  # => true

# With keyword init (3.3+)
class Config < Data.define(:host, :port)
  def self.with_defaults
    new(host: "localhost", port: 3000)
  end
end
```

## String Methods

```ruby
# String#delete_prefix, delete_suffix
"hello_world".delete_prefix("hello_")  # => "world"
"hello_world".delete_suffix("_world")  # => "hello"

# String#start_with? with multiple args
"ruby".start_with?("r", "p")  # => true
"ruby".end_with?("y", "z")    # => true

# String#undump
'"hello\nworld"'.undump  # => "hello\nworld"
```

## Hash Enhancements

```ruby
# Hash#except (Rails backport, now native in 3.0+)
{ a: 1, b: 2, c: 3 }.except(:a)  # => { b: 2, c: 3 }

# Hash#slice (Rails backport, now native)
{ a: 1, b: 2, c: 3 }.slice(:a, :b)  # => { a: 1, b: 2 }

# Transform keys/values with symbols
hash.transform_keys(&:to_s)
hash.transform_values { |v| v * 2 }
```

## Enumerable Improvements

```ruby
# tally - count occurrences
[1, 2, 2, 3, 3, 3].tally  # => { 1 => 1, 2 => 2, 3 => 3 }

# filter_map - filter and map in one pass
(1..10).filter_map { |i| i * 2 if i.even? }  # => [4, 8, 12, 16, 20]

# inject/reduce with init
(1..5).inject(:+)  # => 15
(1..5).inject(10, :+)  # => 25
```

## Time and Duration

```ruby
# ActiveSupport::Duration (Rails)
1.day     # => 1 day
2.hours   # => 7200 seconds
3.minutes # => 180 seconds

# Time calculation
Time.now + 1.day
Time.now - 2.hours

# Beginning/end of time periods
Time.now.beginning_of_day
Time.now.end_of_month
Time.now.next_week
```

## Object#then and Object#yield_self

```ruby
# Pipeline operations
user_data
  .then { |data| JSON.parse(data, symbolize_names: true) }
  .then { |data| validate_user_data(data) }
  .then { |data| User.new(data) }
  .then { |user| user.save! }

# With "it" (Ruby 3.4+)
value
  .then { it.strip.downcase }
  .then { it.gsub(/\s+/, '_') }

# Or with _1 (Ruby 2.7+)
value
  .then { _1.strip.downcase }
  .then { _1.gsub(/\s+/, '_') }
```

## Kernel#tap for Debugging

```ruby
# Inspect intermediate values
result = fetch_data
  .tap { |data| puts "Raw: #{data.inspect}" }
  .then { |data| parse_json(data) }
  .tap { |data| puts "Parsed: #{data.inspect}" }
  .then { |data| transform(data) }
```

## Deprecation Warnings (3.0+)

```ruby
# Built-in deprecation handling
Gem::Deprecate.skip_during { deprecated_call }

# Enable all warnings
ruby -W:all script.rb

# Or in code
$VERBOSE = true
```

## Performance Improvements (3.3+)

```ruby
# YJIT (Just-In-Time compiler)
# - Bare Ruby: not enabled by default; start with --yjit or RUBY_YJIT=1
# - Rails 7.2+: enabled by default when available (Ruby 3.3+)
# Check if enabled
RubyVM::YJIT.enabled?  # => true/false

# Prism parser - pure Ruby parser, faster than ripper
require 'prism'
Prism.parse("1 + 2")
```

## Best Practices for Modern Ruby

```ruby
# Use pattern matching for complex conditionals
case result
in { success: true, data: { users: Array => users } }
  process_users(users)
in { success: false, error: String => msg }
  log_error(msg)
end

# Use endless methods for simple one-liners
def full_name = "#{first_name} #{last_name}"

# Use "it" (Ruby 3.4+) or numbered params for short blocks
# With "it" - clean and readable (Ruby 3.4+)
users.map { it.name }
users.sort_by { it.last_name }

# With numbered params - backward compatible
users.map { _1.name }
users.sort_by { [_1.last_name, _1.first_name] }

# Prefer filter_map over select+map
# Good with "it"
items.filter_map { expensive_op(it) if it.valid? }

# Good with numbered params
items.filter_map { expensive_op(_1) if _1.valid? }

# Avoid - creates intermediate array
items.select(&:valid?).map { expensive_op(_1) }
```
