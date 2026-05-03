# Benchmarking and Profiling

## Benchmark Patterns

### Basic Benchmark

```ruby
# Using standard benchmark library
require 'benchmark'

n = 1000
Benchmark.bm do |x|
  x.report("current:") { n.times { MyModule.current_impl(data) } }
  x.report("optimized:") { n.times { MyModule.optimized_impl(data) } }
end

# Using benchmark-ips gem for iterations per second
gem 'benchmark-ips'
require 'benchmark/ips'

Benchmark.ips do |x|
  x.report("current") { MyModule.current_impl(data) }
  x.report("optimized") { MyModule.optimized_impl(data) }
  x.compare!
end
```

### Benchmark with Setup

```ruby
require 'benchmark'

Benchmark.bm do |x|
  # Setup runs once before benchmark
  posts = Post.all.to_a
  query = Post.joins(:comments).preload(:comments)
  
  x.report("preload:") { 100.times { Post.all.includes(:comments).to_a } }
  x.report("join:") { 100.times { query.to_a } }
end
```

### Comparing Query Strategies

```ruby
require 'benchmark/ips'

Benchmark.ips do |x|
  x.report("separate_queries") do
    posts = Post.all.to_a
    ActiveRecord::Associations::Preloader.new(records: posts, associations: :comments).call
    posts
  end
  
  x.report("join_preload") do
    Post.joins(:comments).preload(:comments).to_a
  end
  
  x.report("eager_load") do
    Post.eager_load(:comments).to_a
  end
  
  x.compare!
end
```

## Active Record Query Analysis

### EXPLAIN ANALYZE

```ruby
# Check query plan for a specific query
result = ActiveRecord::Base.connection.execute(
  "EXPLAIN ANALYZE SELECT * FROM users WHERE email = '#{ActiveRecord::Base.sanitize_sql(['?', 'test@example.com'])}'"
)

# Or using Active Record
puts Post.where(email: "test@example.com").to_explain
```

### Missing Index Detection

```sql
-- Find sequential scans on large tables
SELECT schemaname, relname, seq_scan, seq_tup_read,
       idx_scan, idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > 100
ORDER BY seq_tup_read DESC;
```

```sql
-- Find tables without indexes on foreign keys
SELECT c.conrelid::regclass AS table_name,
       a.attname AS column_name
FROM pg_constraint c
JOIN pg_attribute a ON a.attrelid = c.conrelid AND a.attnum = ANY(c.conkey)
WHERE c.contype = 'f'
AND NOT EXISTS (
  SELECT 1 FROM pg_index i
  WHERE i.indrelid = c.conrelid
  AND a.attnum = ANY(i.indkey)
);
```

### N+1 Detection Patterns

Common patterns that indicate N+1 queries:

```ruby
# Pattern 1: Query inside loop
users.each do |user|
  user.posts.to_a  # Query for each user
end
# Fix: User.includes(:posts).each { ... }

# Pattern 2: Association access without eager load
for post in Post.all
  post.comments.count  # Count query per post
end
# Fix: Post.includes(:comments) or Post.left_joins(:comments).group(:id).select('posts.*, COUNT(comments.id) as comments_count')

# Pattern 3: find inside loop
user_ids.each do |id|
  User.find(id)  # Query per ID
end
# Fix: User.where(id: user_ids)
```

### Bullet Gem (N+1 Detection)

```ruby
# Gemfile
group :development do
  gem 'bullet'
end

# config/environments/development.rb
config.after_initialize do
  Bullet.enable = true
  Bullet.alert = true
  Bullet.bullet_logger = true
  Bullet.console = true
  Bullet.rails_logger = true
  Bullet.add_footer = true
end
```

## Memory Profiling

### MemoryProfiler Gem

```ruby
# Gemfile
gem 'memory_profiler'

# Usage
require 'memory_profiler'

report = MemoryProfiler.report do
  # Code to profile
  User.includes(:posts, :comments).limit(1000).each do |user|
    process(user)
  end
end

report.pretty_print(to_file: 'memory_report.txt')
```

### Object Space Analysis

```ruby
# Check object counts by class
ObjectSpace.each_object(Class).map do |klass|
  [klass.name, ObjectSpace.each_object(klass).count]
end.sort_by { |_, count| -count }.first(10)

# Track memory growth
before = GC.stat(:total_allocated_objects)
# ... run code ...
after = GC.stat(:total_allocated_objects)
puts "Allocated: #{after - before} objects"
```

### Derailed Benchmarks

```ruby
# Gemfile
group :development do
  gem 'derailed_benchmarks'
end

# Test memory usage per request
bundle exec derailed exec perf:mem_over_time

# Test object allocation per request
bundle exec derailed exec perf:objects

# Compare two commits
bundle exec derailed exec perf:mem OVER_FORK=1
```

## Stack Profiling

### StackProf

```ruby
# Gemfile
gem 'stackprof'

# Profile CPU usage
StackProf.run(mode: :cpu, out: 'tmp/stackprof-cpu.dump') do
  # Code to profile
  100.times { expensive_operation }
end

# Profile memory allocation
StackProf.run(mode: :object, out: 'tmp/stackprof-object.dump') do
  # Code to profile
end

# View results
# stackprof tmp/stackprof-cpu.dump --text
# stackprof tmp/stackprof-cpu.dump --method Object#expensive_operation
```

### rbspy (Production Profiling)

| Goal | Command |
|---|---|
| Profile running Ruby process | `sudo rbspy record --pid $PID` |
| Profile for specific duration | `sudo rbspy record --duration 10 --pid $PID` |

## Flame Graph Interpretation

### Generating Flame Graphs

```ruby
# Using stackprof with flamegraph.pl
stackprof tmp/stackprof-cpu.dump --flamegraph > tmp/flamegraph.pl

# Or use speedscope
# Install: npm install -g speedscope
speedscope tmp/stackprof-cpu.dump
```

### Reading Flame Graphs

- **Width** = time spent (wider = slower)
- **Height** = call stack depth
- Look for wide bars at the top (leaf functions consuming time)
- Common culprits: `ActiveRecord::QueryMethods`, `JSON.parse/generate`, `String#gsub`

## Performance Checklist

### Active Record

- [ ] No queries inside loops (`each`, `map`, `select`)
- [ ] Eager load associations with `includes` when needed
- [ ] Frequently queried columns have indexes
- [ ] Large result sets use `find_each` or pagination
- [ ] Aggregations done in SQL, not Ruby
- [ ] Use `pluck` instead of `map` when only need specific columns

### Caching

- [ ] Fragment caching for expensive view partials
- [ ] Low-level caching with `Rails.cache` for expensive calculations
- [ ] Russian doll caching for nested templates
- [ ] HTTP caching headers for API responses

### Memory

- [ ] Avoid loading large datasets into memory
- [ ] Use `find_each` (batches) for iterating over large tables
- [ ] Limit string allocations in hot paths
- [ ] Monitor memory usage in production

### Request Handling

- [ ] Move heavy work to background jobs (Sidekiq)
- [ ] Use `render_async` for slow partials
- [ ] Compress responses with gzip
- [ ] Keep request/response sizes reasonable

### Database

- [ ] Connection pool sized correctly (threads * 1.5)
- [ ] Queries use appropriate indexes
- [ ] No table scans on large tables
- [ ] Write queries batched when possible
