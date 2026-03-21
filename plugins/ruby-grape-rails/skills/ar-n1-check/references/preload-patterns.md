# Preload Patterns

Efficient strategies for loading associations in Active Record.

## Basic Preloading

### Single Association

```ruby
# In query - loads users and their posts in 2 queries
User.includes(:posts)

# Or using preload (same result)
User.preload(:posts)

# In controller
@users = User.includes(:posts)
```

### Nested Associations

```ruby
# Preload nested: user -> posts -> comments
User.includes(posts: :comments)

# Multiple levels
User.includes(posts: [comments: :author])

# Mix includes and joins when needed
User.includes(:profile, posts: :comments)
```

### Multiple Associations

```ruby
# Multiple associations at same level
User.includes(:posts, :comments, :profile)

# Mixed nesting
User.includes(:profile, posts: :comments)
```

## Advanced Preloading

### Custom Scope Preloads

```ruby
# Preload only active posts
User.includes(:posts).where(posts: { active: true })

# Or with separate scope
recent_posts = Post.where("created_at > ?", 1.week.ago)
User.preload(posts: recent_posts)
```

### Preload with Ordering

```ruby
# Order preloaded associations
class User < ApplicationRecord
  has_many :posts, -> { order(created_at: :desc) }
end

# Or inline
User.includes(posts: -> { order(created_at: :desc) })
```

### Preload with Limit

```ruby
# Get only latest 5 posts per user - requires custom query
User.find_each do |user|
  # Bad: N+1 query
  user.posts.limit(5)
end

# Good: Use a custom association with limit
class User < ApplicationRecord
  has_many :recent_posts, -> { order(created_at: :desc).limit(5) }, class_name: "Post"
end

User.includes(:recent_posts)
```

## Eager Loading with Joins

### Filtering by Associations

```ruby
# Find users with published posts (efficient)
User.joins(:posts).where(posts: { published: true }).distinct

# Count with conditions
User.left_joins(:posts)
    .select("users.*, COUNT(posts.id) as posts_count")
    .group("users.id")
```

### Join Preload (eager_load)

```ruby
# Single query with LEFT OUTER JOIN
# Good for small datasets, filters on associations
User.eager_load(:posts, :comments)
    .where(posts: { published: true })

# Same as:
User.includes(:posts, :comments).where(posts: { published: true })
```

## Preloader API (Manual Control)

```ruby
# Manual preloading for already-loaded records
users = User.limit(10).to_a
ActiveRecord::Associations::Preloader.new(
  records: users,
  associations: [:posts, :comments]
).call

# Now posts and comments are loaded
users.each do |user|
  puts user.posts.map(&:title)  # No N+1
end
```

## Anti-patterns

### N+1 Without Preload

```ruby
# BAD: Query for each user's posts
User.all.each do |user|
  puts user.posts.count  # N+1 query
end

# GOOD: Preload first
User.includes(:posts).each do |user|
  puts user.posts.count
end
```

### Preload Without Using

```ruby
# BAD: Preload but don't use it
users = User.includes(:posts)
users.each do |user|
  puts user.name  # Never uses posts
end

# GOOD: Only preload when needed
users = User.all
users.each do |user|
  puts user.name
end
```

### Preload in Loops

```ruby
# BAD: Preload inside loop (inefficient)
organizations.each do |org|
  org.users.includes(:posts).each do |user|
    puts user.posts.map(&:title)
  end
end

# GOOD: Preload at top level
organizations.includes(users: :posts).each do |org|
  org.users.each do |user|
    puts user.posts.map(&:title)
  end
end
```

## Best Practices

### Use Bullet Gem

```ruby
# Gemfile
gem 'bullet', group: :development

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

### Lazy Load in Production

```ruby
# config/environments/production.rb
config.eager_load = true
```

### Always Include in API Controllers

```ruby
# app/controllers/api/posts_controller.rb
def index
  @posts = Post.includes(:author, :comments, :tags)
                 .page(params[:page])
  render json: @posts
end
```
