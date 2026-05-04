# Ruby 3.4 / 4.0 Features Reference

Sources: <https://github.com/ruby/ruby/blob/master/NEWS.md>,
<https://guides.rubyonrails.org/>.

## Pattern Matching (3.0+)

```ruby
case data
in { status: 200, body: String => body }
  puts "Success: #{body}"
in { status: 404 }
  puts "Not found"
in { status: code }
  puts "Error: #{code}"
end

case [1, 2, 3]
in [a, b, c]
  puts "Got #{a}, #{b}, #{c}"
end

case [1, 2, 3, 4, 5]
in [*, 3, *rest]
  puts "Found 3, rest: #{rest.inspect}"
end

case { a: 1, b: 2, c: 3 }
in { a: Integer, **rest }
  puts "a is integer, rest: #{rest.inspect}"
end
```

Find pattern + hash-rest stabilized in 3.2.

## Endless Method Definition (3.0+)

```ruby
def square(x) = x * x
def greet(name) = puts "Hello, #{name}!"
def greet(name = "World") = "Hello, #{name}!"
```

## Numbered Parameters and `it` Keyword

| Style | Use | Constraint |
|---|---|---|
| `it` | Single param, simple expression | Ruby 3.4+; one implicit param only |
| `_1` / `_2` | Multiple implicit params | Ruby 2.7+ |
| Named `\|x\|` | Complex logic, nested blocks | Always available |

```ruby
[1, 2, 3].map { it * 2 }                    # => [2, 4, 6]
users.map { it.name }
items.select { it.price > 10 }
posts.map { it.title.upcase }
products.sort_by { it.price }

[1, 2, 3].map { _1 * 2 }                    # => [2, 4, 6]
[[1, 2], [3, 4]].map { _1 + _2 }            # => [3, 7]
{ a: 1, b: 2 }.each { puts "#{_1}: #{_2}" }
```

Reject:

```ruby
users.map { |u| it.name }            # mixes named + it
users.map { posts.map { it.title } } # ambiguous it
```

Use named params for nested blocks:

```ruby
users.map { |u| u.posts.map { |p| p.title } }
```

## Argument Forwarding (2.7+ enhanced)

```ruby
def wrapper(...)
  target(...)
end

def log_and_call(msg, ...)
  puts msg
  target(...)
end

def with_block(&)
  items.each(&)
end
```

## Fiber Scheduler — async / await (3.0+)

```ruby
require 'async'

Async do
  task1 = Async { fetch_data_from_api }
  task2 = Async { read_from_database }

  data      = task1.wait
  db_result = task2.wait
end

class AsyncController < ApplicationController
  def index
    Async do
      @data = fetch_data
      render json: @data
    end
  end
end
```

## Ractor — true parallelism (3.0+, experimental)

```ruby
ractor = Ractor.new do
  loop do
    msg = Ractor.receive
    puts "Received: #{msg}"
  end
end

ractor.send("Hello from main")

def parallel_map(array, &block)
  ractors = array.map { |item| Ractor.new(item, &block) }
  ractors.map(&:take)
end
```

Ractors enforce strict isolation — share-nothing concurrency.

## Data Classes (3.2+)

```ruby
class Point < Data.define(:x, :y)
  def distance_from_origin
    Math.sqrt(x**2 + y**2)
  end
end

p1 = Point.new(3, 4)
p2 = Point.new(3, 4)
p1 == p2           # => true
p1.hash == p2.hash # => true

class Config < Data.define(:host, :port)
  def self.with_defaults
    new(host: "localhost", port: 3000)
  end
end
```

Keyword init stabilized in 3.3.

## String Methods

```ruby
"hello_world".delete_prefix("hello_")   # => "world"
"hello_world".delete_suffix("_world")   # => "hello"
"ruby".start_with?("r", "p")            # => true
"ruby".end_with?("y", "z")              # => true
'"hello\nworld"'.undump                 # => "hello\nworld"
```

## Hash Enhancements

```ruby
{ a: 1, b: 2, c: 3 }.except(:a)         # => { b: 2, c: 3 }
{ a: 1, b: 2, c: 3 }.slice(:a, :b)      # => { a: 1, b: 2 }
hash.transform_keys(&:to_s)
hash.transform_values { |v| v * 2 }
```

`except` and `slice` are native in 3.0+ (previously Rails-only).

## Enumerable

```ruby
[1, 2, 2, 3, 3, 3].tally                 # => { 1 => 1, 2 => 2, 3 => 3 }
(1..10).filter_map { |i| i * 2 if i.even? }  # => [4, 8, 12, 16, 20]
(1..5).inject(:+)                        # => 15
(1..5).inject(10, :+)                    # => 25
```

## Time and Duration (Rails / ActiveSupport)

```ruby
1.day      # 86400 seconds
2.hours    # 7200 seconds
3.minutes  # 180 seconds

Time.now + 1.day
Time.now - 2.hours
Time.now.beginning_of_day
Time.now.end_of_month
Time.now.next_week
```

## `Object#then` / `yield_self`

```ruby
user_data
  .then { |data| JSON.parse(data, symbolize_names: true) }
  .then { |data| validate_user_data(data) }
  .then { |data| User.new(data) }
  .then { |user| user.save! }

value
  .then { it.strip.downcase }
  .then { it.gsub(/\s+/, '_') }

value
  .then { _1.strip.downcase }
  .then { _1.gsub(/\s+/, '_') }
```

## `Kernel#tap` for inline inspection

```ruby
result = fetch_data
  .tap { |data| puts "Raw: #{data.inspect}" }
  .then { |data| parse_json(data) }
  .tap { |data| puts "Parsed: #{data.inspect}" }
  .then { |data| transform(data) }
```

## Deprecation Warnings (3.0+)

```ruby
Gem::Deprecate.skip_during { deprecated_call }

# enable all warnings: `ruby -W:all script.rb`
$VERBOSE = true
```

## Performance (3.3+)

```ruby
RubyVM::YJIT.enabled?   # => true/false
require 'prism'
Prism.parse("1 + 2")
```

| Item | Status |
|---|---|
| YJIT in bare Ruby | Off by default; enable with `--yjit` or `RUBY_YJIT=1` |
| YJIT in Rails 7.2+ | On by default when Ruby 3.3+ available |
| Prism | Pure-Ruby parser, faster than Ripper |

## Modern-Ruby Idioms

| Pattern | Form |
|---|---|
| Complex conditional dispatch | `case ... in ...` pattern matching |
| Single-line method | `def x = body` |
| Single-arg short block (3.4+) | `{ it.name }` |
| Single-arg short block (≥2.7) | `{ _1.name }` |
| Filter + map | `filter_map { ... }` |

```ruby
case result
in { success: true, data: { users: Array => users } }
  process_users(users)
in { success: false, error: String => msg }
  log_error(msg)
end

def full_name = "#{first_name} #{last_name}"

users.map { it.name }
users.sort_by { it.last_name }

users.map { _1.name }
users.sort_by { [_1.last_name, _1.first_name] }

items.filter_map { expensive_op(it) if it.valid? }
items.filter_map { expensive_op(_1) if _1.valid? }
```

Reject `select(&:valid?).map { expensive_op(_1) }` — two passes,
intermediate array.
