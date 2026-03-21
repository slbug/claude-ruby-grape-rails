# Query Optimization Techniques

Strategies for optimizing ActiveRecord queries and eliminating N+1 patterns.

## Batching Queries

### Replace Loop Queries with IN Clause

```ruby
# BAD: N queries
user_ids.each do |id|
  User.find(id)
end

# GOOD: Single query
User.where(id: user_ids)
```

### Batch Inserts

```ruby
# BAD: N inserts
items.each do |item|
  Item.create!(item)
end

# GOOD: Single insert_all (Rails 6+)
Item.insert_all(items)

# Or with upsert (Rails 6+)
Item.upsert_all(items, unique_by: :index_items_on_external_id)
```

### Batch Updates

```ruby
# BAD: N updates
users.each do |user|
  user.update!(active: false)
end

# GOOD: Single update_all
User.where(id: user_ids).update_all(active: false, updated_at: Time.current)

# For conditional updates with touch
User.where(id: user_ids).update_all("active = NOT active, updated_at = NOW()")
```

## Query Composition

### Composable Query Methods

```ruby
# app/queries/user_query.rb
class UserQuery
  def self.base
    User.all
  end

  def self.active(scope = base)
    scope.where(active: true)
  end

  def self.with_posts(scope = base)
    scope.includes(:posts)
  end

  def self.recent(scope = base, days = 30)
    cutoff = days.days.ago
    scope.where("created_at > ?", cutoff)
  end
end

# Usage: Compose queries
UserQuery.base
  .then { |s| UserQuery.active(s) }
  .then { |s| UserQuery.with_posts(s) }
  .then { |s| UserQuery.recent(s, 7) }
  .to_a

# Or chain directly
User.active.includes(:posts).where("created_at > ?", 7.days.ago)
```

## Subqueries for Complex Filtering

### EXISTS Subquery

```ruby
# Find users with at least one published post
User
  .where_exists(:posts, published: true)
  .to_a

# Using Arel for complex conditions
User.where(
  Post.where("posts.user_id = users.id")
      .where(published: true)
      .arel.exists
)
```

### Count Subquery

```ruby
# Get users with post counts (single query)
User
  .select("users.*, COUNT(posts.id) as posts_count")
  .left_joins(:posts)
  .group("users.id")
  .having("COUNT(posts.id) > 0")
  .to_a

# user.posts_count available without N+1
```

### Subquery in WHERE

```ruby
# Find users who have posts in specific categories
category_post_ids = Post.where(category: 'tech').select(:user_id)

User.where(id: category_post_ids)
```

## Window Functions (PostgreSQL)

### ROW_NUMBER for Ranking

```ruby
# Rank users by order count per organization
User.select(<<~SQL
  users.*,
  ROW_NUMBER() OVER (
    PARTITION BY organization_id 
    ORDER BY orders_count DESC
  ) as rank
SQL
).from(
  User.select("users.*, COUNT(orders.id) as orders_count")
      .joins("LEFT JOIN orders ON orders.user_id = users.id")
      .group("users.id, users.organization_id"),
  :users
)
```

### LAG/LEAD for Time Series

```ruby
# Compare current order with previous
Order.select(<<~SQL
  orders.*,
  LAG(total) OVER (
    PARTITION BY user_id 
    ORDER BY created_at
  ) as previous_order_total,
  total - LAG(total) OVER (
    PARTITION BY user_id 
    ORDER BY created_at
  ) as total_change
SQL
)
```

## CTE (Common Table Expressions)

### Recursive CTE for Hierarchies

```ruby
# Find all descendants in tree structure
hierarchy_sql = <<~SQL
  WITH RECURSIVE descendants AS (
    SELECT id, parent_id, 0 as depth
    FROM categories
    WHERE id = ?
    
    UNION ALL
    
    SELECT c.id, c.parent_id, d.depth + 1
    FROM categories c
    INNER JOIN descendants d ON c.parent_id = d.id
  )
  SELECT * FROM descendants
SQL

Category.find_by_sql([hierarchy_sql, root_category_id])
```

### Non-Recursive CTE

```ruby
# Complex reporting with intermediate results
report_sql = <<~SQL
  WITH monthly_stats AS (
    SELECT 
      user_id,
      DATE_TRUNC('month', created_at) as month,
      SUM(amount) as total,
      COUNT(*) as count
    FROM orders
    WHERE created_at > NOW() - INTERVAL '12 months'
    GROUP BY user_id, DATE_TRUNC('month', created_at)
  )
  SELECT 
    user_id,
    AVG(total) as avg_monthly_revenue,
    SUM(total) as yearly_revenue
  FROM monthly_stats
  GROUP BY user_id
SQL

Order.connection.select_all(report_sql)
```

## Raw SQL When Needed

### Complex Joins

```ruby
# Multi-table join with complex conditions
sql = <<~SQL
  SELECT users.*, orders.id as order_id, products.name as product_name
  FROM users
  INNER JOIN orders ON orders.user_id = users.id
  INNER JOIN order_items ON order_items.order_id = orders.id
  INNER JOIN products ON products.id = order_items.product_id
  WHERE users.active = true
    AND orders.created_at > NOW() - INTERVAL '30 days'
  ORDER BY orders.created_at DESC
SQL

User.find_by_sql(sql)
```

### PostgreSQL-Specific Features

```ruby
# JSONB operations
User.where("settings @> ?", { theme: "dark" }.to_json)

# Array operations
User.where("? = ANY(tags)", "ruby")

# Full-text search
User.where("to_tsvector('english', name || ' ' || bio) @@ to_tsquery('ruby & rails')")

# Geospatial (with PostGIS extension)
Location.where(
  "ST_DWithin(coordinates, ST_SetSRID(ST_MakePoint(?, ?), 4326), ?)",
  longitude, latitude, 1000 # meters
)
```

## Query Caching

### Rails Query Cache

```ruby
# Within a block, identical queries are cached
ActiveRecord::Base.cache do
  # First query hits database
  user = User.find(1)
  
  # Second query returns cached result
  user = User.find(1)
end

# Or enable for entire controller action
class UsersController < ApplicationController
  def show
    # All queries in this action are cached
    @user = User.includes(:posts, :comments).find(params[:id])
  end
end
```

### Fragment Caching

```erb
<% cache ["user-stats", @user, @user.posts.maximum(:updated_at)] do %>
  <div class="stats">
    <p>Posts: <%= @user.posts.count %></p>
    <p>Comments: <%= @user.comments.count %></p>
  </div>
<% end %>
```

## N+1 Prevention Checklist

- [ ] Use `includes` for associations that will be accessed
- [ ] Use `preload` when you don't need to filter by association
- [ ] Use `eager_load` when filtering by association (LEFT JOIN)
- [ ] Never call `count`, `first`, `last` on associations in loops
- [ ] Use `ids` instead of `map(&:id)` for getting IDs
- [ ] Use `pluck` instead of `map` for getting single columns
- [ ] Consider `find_each` for large batches

## Modern Ruby/Rails Patterns (2026)

### Using `it` keyword (Ruby 3.4+)

```ruby
# Before Ruby 3.4
users.map { _1.name }

# Ruby 3.4+
users.map { it.name }
```

### Using `filter_map` (Ruby 2.7+)

```ruby
# Old way - creates intermediate array
users.select(&:active?).map { it.name }

# Modern way - single pass
users.filter_map { it.name if it.active? }
```

### Using `in_order_of` (Rails 7+)

```ruby
# Order by specific sequence
User.in_order_of(:role, %w[admin moderator user])

# With additional ordering
User.in_order_of(:id, priority_ids).order(:created_at)
```

### Using `async` queries (Rails 8+)

```ruby
# Execute queries asynchronously
users = User.where(active: true).async_load
posts = Post.recent.async_load

# Both queries run in parallel
render json: { users: users.value, posts: posts.value }
```

## Performance Monitoring

### Using Bullet Gem

```ruby
# config/environments/development.rb
config.after_initialize do
  Bullet.enable = true
  Bullet.alert = true
  Bullet.bullet_logger = true
  Bullet.console = true
  Bullet.add_footer = true
  Bullet.skip_html_injection = false
  Bullet.stacktrace_includes = %w[your_gem your_middleware]
  Bullet.stacktrace_excludes = %w[their_gem their_middleware]
end
```

### Using rack-mini-profiler

```ruby
# Gemfile
gem 'rack-mini-profiler'

# Automatically profiles all queries
# Look for "SQL" section in profiler bar
```

### Query Log Tags (Rails 7+)

```ruby
# config/application.rb
config.active_record.query_log_tags_enabled = true
config.active_record.query_log_tags = %i[application controller action job pid]

# Output: /*application:MyApp,controller:users,action:index,pid:1234*/ SELECT * FROM users
```
