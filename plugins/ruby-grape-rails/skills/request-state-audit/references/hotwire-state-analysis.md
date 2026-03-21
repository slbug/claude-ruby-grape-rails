# Hotwire State Analysis

Audit controller instance variables and Turbo Stream data for performance issues.

## What to Analyze

### Controller Instance Variables

```ruby
# app/controllers/posts_controller.rb
def index
  # ❌ Loading too much into instance variables
  @posts = Post.all.includes(:comments, :author, :tags)
  @recent_comments = Comment.recent.limit(100)
  @tags = Tag.all
  @stats = calculate_expensive_stats
  @users = User.active
  
  # ❌ N+1 in view through instance variables
  @posts.each do |post|
    @authors[post.id] = post.author # Lazy load in loop
  end
end
```

### Stream Data

```ruby
# ❌ Broadcasting heavy objects
after_create_commit -> { 
  broadcast_prepend_to "posts", 
    partial: "posts/post_with_comments",
    locals: { 
      post: self,
      comments: comments.includes(:author, :replies), # Heavy
      stats: calculate_stats # Expensive
    }
}

# ✅ Stream minimal data
after_create_commit -> { 
  broadcast_prepend_to "posts", 
    partial: "posts/post",
    target: "posts"
}
```

## Iron Laws

1. **Never query the database in Turbo Stream responses** - Pre-compute before broadcast
2. **Keep instance variables minimal** - Only what the view needs
3. **Use fragment caching** for expensive partials
4. **Preload associations** before setting instance variables, not in views
5. **Stream IDs, not objects** - Let client fetch details if needed

## Analysis Checklist

- [ ] Heavy instance variables in controllers
- [ ] Missing includes causing N+1 in views
- [ ] Expensive calculations in stream broadcasts
- [ ] Transient data persisted in instance variables
- [ ] Missing fragment caching on partials
- [ ] Broadcasting before transaction commit

## Output

Return findings with severity and fix suggestions:

```
## Hotwire State Analysis

### Critical
- posts#index: @stats loads 5000 records (suggest: background job)

### High
- Comment broadcasts include replies (suggest: stream ID only)

### Medium
- posts/show missing fragment cache on comments partial
```
