# Queries Reference

## Composable Query Methods

```ruby
class PostQuery
  def self.base
    Post.all
  end

  def self.published(scope = base)
    scope.where.not(published_at: nil)
  end

  def self.by_author(scope = base, author_id)
    scope.where(author_id: author_id)
  end

  def self.recent(scope = base, days = 7)
    cutoff = days.days.ago
    scope.where("created_at >= ?", cutoff)
  end

  def self.ordered(scope = base, direction = :desc)
    scope.order(created_at: direction)
  end
end

# Usage: Method chaining composition
PostQuery.published
  .by_author(author_id)
  .ordered
  .to_a
```

## Dynamic Queries

```ruby
def filter_where(params)
  scope = Post.all

  params.each do |key, value|
    case key
    when "author"
      scope = scope.where(author: value)
    when "category"
      scope = scope.where(category: value)
    when "title_contains"
      scope = scope.where("title ILIKE ?", "%#{value}%")
    end
  end

  scope
end

# Usage
def list_posts(params)
  filter_where(params)
end
```

## Subqueries

```ruby
# Correlated subquery
comment_count = Comment.where("comments.post_id = posts.id").select("COUNT(*)")

Post.select(:title, :id)
    .select("(#{comment_count.to_sql}) as comment_count")
```

## Window Functions

```ruby
# Using Arel for window functions
Post.select(:id, :title)
    .select("ROW_NUMBER() OVER (PARTITION BY category_id ORDER BY created_at) as row_num")
    .select("RANK() OVER (PARTITION BY category_id ORDER BY view_count DESC) as rank")
```

## JSONB Queries (PostgreSQL)

### jsonb_extract_path

Extract values from JSONB columns:

```ruby
# Extract nested JSON value
User.where("settings->'notifications'->>'email' = ?", "true")
    .select("metadata->>'theme' as theme")

# Compare with older approach
User.where("metadata @> ?", {theme: "dark"}.to_json)
```

### JSONB Indexing

```ruby
# Migration
add_index :users, "(settings->>'theme')", name: "index_users_on_theme"
add_index :users, :metadata, using: :gin, name: "index_users_on_metadata"
```

## Anti-patterns

```ruby
# WRONG: SQL injection risk
Post.where("title = '#{user_input}'")

# RIGHT: Parameterized
Post.where("title = ?", user_input)

# WRONG: N+1 query
Post.all.each { |p| puts p.author.name }

# RIGHT: Eager loading
Post.includes(:author).each { |p| puts p.author.name }
```
