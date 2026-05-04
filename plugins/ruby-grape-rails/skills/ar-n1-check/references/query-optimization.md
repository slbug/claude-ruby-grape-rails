# Query Optimization Techniques

Eliminate N+1 patterns and reduce ActiveRecord query count.

## Batching Queries

### Replace per-row lookup with `IN` clause

Reject per-id loop:

```ruby
user_ids.each do |id|
  User.find(id)
end
```

Use a single batched query:

```ruby
User.where(id: user_ids)
```

### Batch inserts

Use `insert_all` / `upsert_all` (Rails 6+):

```ruby
Item.insert_all(items)
Item.upsert_all(items, unique_by: :index_items_on_external_id)
```

`create!` per row is the wrong tool when callbacks/validations are
not required.

### Batch updates

```ruby
User.where(id: user_ids).update_all(active: false, updated_at: Time.current)
```

For conditional toggle:

```ruby
User.where(id: user_ids).update_all("active = NOT active, updated_at = NOW()")
```

`update_all` skips callbacks and validations — confirm acceptable
before adopting.

## Query Composition

```ruby
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
    scope.where("created_at > ?", days.days.ago)
  end
end

UserQuery.base
  .then { |s| UserQuery.active(s) }
  .then { |s| UserQuery.with_posts(s) }
  .then { |s| UserQuery.recent(s, 7) }
  .to_a

User.active.includes(:posts).where("created_at > ?", 7.days.ago)
```

## Subqueries for Complex Filtering

### EXISTS subquery

Rails 6.1+ ships `where.associated(:assoc)` and `where.missing(:assoc)`
in core; both compile to SQL `EXISTS` / `NOT EXISTS` against the
association.

```ruby
User.where.associated(:posts).where(posts: { published: true })
```

For Rails versions before 6.1, or when filtering by a relation that
isn't expressible as a single association, use the Arel `exists`
form:

```ruby
User.where(
  Post.where("posts.user_id = users.id")
      .where(published: true)
      .arel.exists
)
```

The `where_exists` method seen in older blog posts is a third-party
gem (`EugZol/where_exists`), not core ActiveRecord. Prefer the core
forms above.

### Aggregate via single query

```ruby
User
  .select("users.*, COUNT(posts.id) AS posts_count")
  .left_joins(:posts)
  .group("users.id")
  .having("COUNT(posts.id) > 0")
  .to_a
```

`posts_count` becomes a memoized attribute on each row.

### Subquery in `WHERE`

```ruby
category_post_ids = Post.where(category: 'tech').select(:user_id)
User.where(id: category_post_ids)
```

`select(:user_id)` keeps execution as a single SQL statement.

## Window Functions (PostgreSQL)

### `ROW_NUMBER` ranking

```ruby
User.select(<<~SQL)
  users.*,
  ROW_NUMBER() OVER (
    PARTITION BY organization_id
    ORDER BY orders_count DESC
  ) AS rank
SQL
.from(
  User.select("users.*, COUNT(orders.id) AS orders_count")
      .joins("LEFT JOIN orders ON orders.user_id = users.id")
      .group("users.id, users.organization_id"),
  :users
)
```

### `LAG` / `LEAD` for time series

```ruby
Order.select(<<~SQL)
  orders.*,
  LAG(total) OVER (PARTITION BY user_id ORDER BY created_at) AS previous_order_total,
  total - LAG(total) OVER (PARTITION BY user_id ORDER BY created_at) AS total_change
SQL
```

## CTE (Common Table Expressions)

### Recursive CTE — tree descendants

```ruby
hierarchy_sql = <<~SQL
  WITH RECURSIVE descendants AS (
    SELECT id, parent_id, 0 AS depth
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

### Non-recursive CTE — reporting

```ruby
report_sql = <<~SQL
  WITH monthly_stats AS (
    SELECT
      user_id,
      DATE_TRUNC('month', created_at) AS month,
      SUM(amount) AS total,
      COUNT(*) AS count
    FROM orders
    WHERE created_at > NOW() - INTERVAL '12 months'
    GROUP BY user_id, DATE_TRUNC('month', created_at)
  )
  SELECT
    user_id,
    AVG(total) AS avg_monthly_revenue,
    SUM(total) AS yearly_revenue
  FROM monthly_stats
  GROUP BY user_id
SQL

Order.connection.select_all(report_sql)
```

## Raw SQL

Use `find_by_sql` only when the relation builder cannot express the
join shape:

```ruby
sql = <<~SQL
  SELECT users.*, orders.id AS order_id, products.name AS product_name
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

### PostgreSQL-specific operators

```ruby
User.where("settings @> ?", { theme: "dark" }.to_json)
User.where("? = ANY(tags)", "ruby")
User.where("to_tsvector('english', name || ' ' || bio) @@ to_tsquery('ruby & rails')")

Location.where(
  "ST_DWithin(coordinates, ST_SetSRID(ST_MakePoint(?, ?), 4326), ?)",
  longitude, latitude, 1000
)
```

Iron Law 2 / 15: never interpolate; always use placeholders.

## Query Caching

### Block-level cache

```ruby
ActiveRecord::Base.cache do
  user = User.find(1)
  user = User.find(1) # served from cache
end
```

Rails caches identical queries within the same controller action by
default. Wrap explicit blocks for non-controller code.

### Fragment cache key from association timestamp

```erb
<% cache ["user-stats", @user, @user.posts.maximum(:updated_at)] do %>
  <div class="stats">
    <p>Posts: <%= @user.posts.count %></p>
    <p>Comments: <%= @user.comments.count %></p>
  </div>
<% end %>
```

## N+1 Prevention Checklist

- [ ] `includes` for associations the view/serializer will read
- [ ] `preload` when no association predicate is needed
- [ ] `eager_load` when filtering by association (LEFT JOIN)
- [ ] No `count` / `first` / `last` on associations inside loops
- [ ] `ids` over `map(&:id)`
- [ ] `pluck` over `map` for single columns
- [ ] `find_each` for large batches

## Modern Ruby/Rails Patterns

### `it` keyword (Ruby 3.4+)

```ruby
users.map { it.name }
```

### `filter_map` (Ruby 2.7+)

```ruby
users.filter_map { it.name if it.active? }
```

Single-pass filter+map; no intermediate `select`.

### `in_order_of` (Rails 7+)

```ruby
User.in_order_of(:role, %w[admin moderator user])
User.in_order_of(:id, priority_ids).order(:created_at)
```

### Async queries (Rails 8+)

```ruby
users = User.where(active: true).async_load
posts = Post.recent.async_load

render json: { users: users.value, posts: posts.value }
```

Both relations dispatch in parallel; `.value` blocks until each
resolves.

## Performance Monitoring

### Bullet gem

```ruby
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

### rack-mini-profiler

```ruby
gem 'rack-mini-profiler'
```

Adds a profiler bar with per-request SQL summary.

### Query log tags (Rails 7+)

```ruby
config.active_record.query_log_tags_enabled = true
config.active_record.query_log_tags = %i[application controller action job pid]
```

Each query is annotated with a SQL comment carrying the originating
controller/job, useful for slow-query log triage.
