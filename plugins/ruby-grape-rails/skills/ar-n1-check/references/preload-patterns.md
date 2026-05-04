# Preload Patterns

Strategies for loading Active Record associations without N+1.

## Basic Preloading

### Single association

```ruby
User.includes(:posts)
User.preload(:posts)
```

`includes` and `preload` both issue 2 queries. Use `includes` by
default; it can switch to JOIN automatically when the association is
referenced in `where`/`order`. Use `preload` when forcing the
two-query path.

### Nested associations

```ruby
User.includes(posts: :comments)
User.includes(posts: [comments: :author])
User.includes(:profile, posts: :comments)
```

### Multiple associations at the same level

```ruby
User.includes(:posts, :comments, :profile)
```

## Advanced Preloading

### Filter preloaded scope

```ruby
User.includes(:posts).where(posts: { active: true })
```

Forces JOIN form when the `where` references the included table.

### Order preloaded records

```ruby
class User < ApplicationRecord
  has_many :posts, -> { order(created_at: :desc) }
end

User.includes(posts: -> { order(created_at: :desc) })
```

### Preload with limit per parent

`limit` inside an iterated `has_many` triggers N+1. Define a separate
scoped association:

```ruby
class User < ApplicationRecord
  has_many :recent_posts, -> { order(created_at: :desc).limit(5) }, class_name: "Post"
end

User.includes(:recent_posts)
```

## Eager Loading with Joins

### Filter parents by association predicate

```ruby
User.joins(:posts).where(posts: { published: true }).distinct

User.left_joins(:posts)
    .select("users.*, COUNT(posts.id) AS posts_count")
    .group("users.id")
```

### `eager_load` (single LEFT OUTER JOIN)

```ruby
User.eager_load(:posts, :comments)
    .where(posts: { published: true })
```

Equivalent to `includes(...).where(...)` when `where` references the
included table. Single SQL round-trip; row count multiplies by joined
rows — fine for small parent sets, costly for wide associations.

## Manual Preloader API

For records already loaded into memory:

```ruby
users = User.limit(10).to_a
ActiveRecord::Associations::Preloader.new(
  records: users,
  associations: [:posts, :comments]
).call
```

## Anti-patterns

### Iterate without preload (N+1)

Reject:

```ruby
User.all.each do |user|
  puts user.posts.count
end
```

Fix:

```ruby
User.includes(:posts).each do |user|
  puts user.posts.count
end
```

### Preload an unused association

Reject:

```ruby
users = User.includes(:posts)
users.each { |user| puts user.name }
```

Drop the include when the association is not read.

### Preload inside a loop

Reject:

```ruby
organizations.each do |org|
  org.users.includes(:posts).each do |user|
    puts user.posts.map(&:title)
  end
end
```

Fix at the top level:

```ruby
organizations.includes(users: :posts).each do |org|
  org.users.each do |user|
    puts user.posts.map(&:title)
  end
end
```

## Practices

### Bullet gem (development)

```ruby
gem 'bullet', group: :development
```

```ruby
config.after_initialize do
  Bullet.enable = true
  Bullet.alert = true
  Bullet.bullet_logger = true
  Bullet.console = true
  Bullet.rails_logger = true
  Bullet.add_footer = true
end
```

### Eager load in production

```ruby
config.eager_load = true
```

### API controllers — preload before render

```ruby
def index
  @posts = Post.includes(:author, :comments, :tags).page(params[:page])
  render json: @posts
end
```
