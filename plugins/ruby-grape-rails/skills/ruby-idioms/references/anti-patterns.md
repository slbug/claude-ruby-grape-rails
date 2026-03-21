# Anti-Patterns Reference

## Memory & Performance

```ruby
# WRONG: size for empty check (O(n) for some collections)
array.size == 0

# RIGHT: Use empty? or none?
array.empty?
array.none?

# WRONG: += to append (creates new array each time)
array += [item]

# RIGHT: Use << for single item, concat for multiple
array << item
array.concat(other_array)

# WRONG: Dynamic constant creation (causes warnings, thread-unsafe)
Object.const_set(user_input, value)

# RIGHT: Use a hash or existing constants
STATUS_MAP = {
  "ok" => :ok,
  "error" => :error
}.freeze
STATUS_MAP[user_input]

# WRONG: Sending unnecessary data (copies large objects)
Thread.new { process_data(large_hash) }  # Copies entire hash!
Sidekiq::Client.push('args' => [large_object.id])  # Copies entire object!

# RIGHT: Extract minimal data before spawning or sending
item_id = large_hash[:id]
Thread.new { process_data(item_id) }
Sidekiq::Client.push('args' => [large_object.id])
```

## String Handling

```ruby
# WRONG: String concatenation in loops (creates many objects)
result = ""
items.each { |item| result += item.to_s }

# RIGHT: Use array join
result = items.map(&:to_s).join

# WRONG: Repeated substrings keeping large parent alive
small = large_string[0..100]  # Reference to large_string

# RIGHT: Force copy if keeping only small part
small = large_string[0..100].dup
```

## Code Organization

```ruby
# WRONG: Deeply nested conditionals
if user
  if user.subscription
    if user.subscription.active?
      if user.subscription.includes?(feature)
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

# RIGHT: Early returns
def check_access(user, feature)
  return :user_not_found unless user
  return :no_subscription unless user.subscription
  return :subscription_inactive unless user.subscription.active?
  return :feature_not_included unless user.subscription.includes?(feature)
  
  :ok
end

# WRONG: Metaprogramming when simple method works
class_eval <<-RUBY
  def #{name}
    @#{name}
  end
RUBY

# RIGHT: Just use attr_accessor
attr_accessor name
```

## ActiveRecord Anti-Patterns

```ruby
# ANTI-PATTERN: N+1 query without includes
User.all.each do |user|
  puts user.posts.count  # Query for each user!
end

# CORRECT: Eager load associations
User.includes(:posts).each do |user|
  puts user.posts.count
end

# ANTI-PATTERN: Loading all records into memory
User.all.each { |u| process(u) }  # Memory explosion with 1M users

# CORRECT: Use find_each for batch processing
User.find_each(batch_size: 1000) { |u| process(u) }

# ANTI-PATTERN: Updating one by one
users.each { |u| u.update(active: true) }  # N queries

# CORRECT: Update in batches
User.where(active: false).update_all(active: true)
# Or for callbacks:
User.where(active: false).find_each { |u| u.update!(active: true) }
```

## Assertiveness (Fail Fast)

```ruby
# WRONG: Silent nil returns — hides bugs
data[:key]  # Returns nil if missing

# RIGHT: Fail fast or use fetch with default
data.fetch(:key)  # Raises KeyError if missing
data.fetch(:key, default_value)  # Or provide default
data[:key] || raise(KeyError, "Missing key: :key")  # Explicit

# WRONG: Catch-all rescue hides errors
begin
  risky_operation
rescue => e  # Catches EVERYTHING!
  :error
end

# RIGHT: Match specific errors
begin
  risky_operation
rescue ActiveRecord::RecordNotFound
  :not_found
rescue ArgumentError => e
  logger.error "Invalid argument: #{e.message}"
  :invalid
end

# WRONG: Boolean obsession — multiple related booleans
user.is_admin? && !user.is_editor? && !user.is_viewer?

# RIGHT: Single role field
user.role == :admin
# Or use enum:
enum role: { admin: 0, editor: 1, viewer: 2 }
```

## Lazy vs Eager Loading

```ruby
# Lazy enumeration — only computes what's needed
(1..1_000_000)
  .lazy
  .map { |i| expensive_operation(i) }
  .select { |x| valid?(x) }
  .first(5)
  .force  # Only processes ~5 elements

# Eager enumeration — entire collection each step
(1..1_000_000)
  .map { |i| expensive_operation(i) }      # Creates 1M array
  .select { |x| valid?(x) }                 # Creates another array
  .first(5)
```

**Use `lazy`** for large collections, multiple transformations, memory constraints.
**Use eager** for small/medium collections, immediate results.

## Method Chaining

```ruby
# AVOID: Chain with single step
name.upcase.strip  # Just: name.upcase.strip (still a chain)

# AVOID: Start with complex expression
User.where(active: true).first.name  # Use find_by instead

# DO: Use tap for side effects (returns original value)
user
  .tap { |u| Rails.logger.info("Processing user: #{u.id}") }
  .then { |u| process(u) }

# DO: Use then for transformations (Ruby 2.5+)
user
  .then { |u| format_name(u) }
  .then { |n| n.upcase }
  .then { |n| { name: n } }

# Or with "it" keyword (Ruby 3.4+)
user
  .then { it.name }
  .then { it.upcase }
  .then { { name: it } }
```

## Binary/String Handling

```ruby
# ANTI-PATTERN: Substring keeps large parent alive
small = large_string[0, 100]  # May reference large_string

# DO: Force copy if keeping only the small part
small = large_string[0, 100].dup

# WRONG: Inefficient string building
html = "<div>"
items.each { |item| html += "<p>#{item}</p>" }
html += "</div>"

# RIGHT: Use array join or heredoc
html = items.map { |item| "<p>#{item}</p>" }.join.prepend("<div>").concat("</div>")
# Or better, use a template engine
```

## Recursion

Ruby doesn't optimize tail recursion by default. Use iteration for large datasets:

```ruby
# Not optimized - builds stack
factorial(0) = 1
factorial(n) = n * factorial(n - 1)  # Stack grows

# Better - use iteration
factorial(n)
  result = 1
  n.downto(1) { |i| result *= i }
  result
end

# Or use reduce
(1..n).reduce(1, :*)
```

**Rule of thumb**: Use iteration or Enumerable methods for 95% of cases—cleaner and well-tested.
