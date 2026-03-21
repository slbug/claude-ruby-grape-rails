# Turbo Streams Navigation Reference

## Turbo Streams Broadcasting Pattern

### Model-Based Broadcasting

```ruby
# app/models/post.rb
class Post < ApplicationRecord
  belongs_to :user
  has_many :comments, dependent: :destroy
  
  # Broadcast to all subscribers
  after_create_commit -> { broadcast_prepend_to "posts" }
  after_update_commit -> { broadcast_replace_to "posts" }
  after_destroy_commit -> { broadcast_remove_to "posts" }
end

# app/views/posts/index.html.erb
<%= turbo_stream_from "posts" %>

<div id="posts">
  <%= render @posts %>
</div>

# app/views/posts/_post.html.erb
<%= turbo_frame_tag post do %>
  <article class="post">
    <h3><%= post.title %></h3>
    <p><%= post.body %></p>
    <footer>
      Posted by <%= post.user.name %> 
      <%= time_tag post.created_at, time_ago_in_words(post.created_at) %> ago
    </footer>
  </article>
<% end %>
```

### Scoped Broadcasting

```ruby
# app/models/comment.rb
class Comment < ApplicationRecord
  belongs_to :post
  belongs_to :user
  
  # Broadcast only to subscribers of this post
  after_create_commit -> { broadcast_append_to [post, :comments], target: "comments" }
  after_destroy_commit -> { broadcast_remove_to [post, :comments] }
end

# app/views/posts/show.html.erb
<%= turbo_stream_from @post, :comments %>

<h1><%= @post.title %></h1>
<p><%= @post.body %></p>

<h2>Comments</h2>
<div id="comments">
  <%= render @post.comments %>
</div>

<%= turbo_frame_tag dom_id(@post, :new_comment) do %>
  <%= render "comments/form", post: @post %>
<% end %>
```

## Custom Broadcasting

### From Controllers

```ruby
# app/controllers/posts_controller.rb
class PostsController < ApplicationController
  def create
    @post = current_user.posts.build(post_params)
    
    if @post.save
      # Notify followers
      current_user.followers.each do |follower|
        Turbo::StreamsChannel.broadcast_prepend_to(
          [follower, :feed],
          target: "feed",
          partial: "posts/post",
          locals: { post: @post }
        )
      end
      
      respond_to do |format|
        format.html { redirect_to @post }
        format.turbo_stream { render turbo_stream: turbo_stream.replace("new_post", "") }
      end
    else
      render :new, status: :unprocessable_entity
    end
  end
  
  def destroy
    @post = current_user.posts.find(params[:id])
    @post.destroy
    
    # Broadcast removal to all subscribed pages
    Turbo::StreamsChannel.broadcast_remove_to(
      "posts",
      target: dom_id(@post)
    )
    
    respond_to do |format|
      format.html { redirect_to posts_path }
      format.turbo_stream
    end
  end
end
```

### From Service Objects

```ruby
# app/services/notification_service.rb
class NotificationService
  def self.notify_mention(user, post, mentioner)
    notification = user.notifications.create!(
      post: post,
      mentioner: mentioner,
      type: :mention
    )
    
    # Real-time notification
    Turbo::StreamsChannel.broadcast_prepend_to(
      [user, :notifications],
      target: "notifications",
      partial: "notifications/notification",
      locals: { notification: notification }
    )
    
    # Update notification count badge
    Turbo::StreamsChannel.broadcast_replace_to(
      [user, :notification_count],
      target: "notification-count",
      html: ApplicationController.render(
        partial: "shared/notification_badge",
        locals: { count: user.notifications.unread.count }
      )
    )
  end
end
```

## Navigation Patterns

### Turbo Drive Navigation

```erb
<!-- Links use Turbo Drive by default -->
<%= link_to "Posts", posts_path %>
<%= link_to "User Profile", user_path(@user) %>

<!-- Opt out for specific links -->
<%= link_to "External Site", "https://example.com", data: { turbo: false } %>

<!-- Force full page reload -->
<%= link_to "PDF Download", document_path(@doc), data: { turbo: false } %>
```

### Turbo Frames Navigation

```erb
<!-- app/views/layouts/application.html.erb -->
<!DOCTYPE html>
<html>
  <body>
    <nav><!-- Navigation persists --></nav>
    
    <%= yield %>
    
    <footer><!-- Footer persists --></footer>
  </body>
</html>

<!-- app/views/users/show.html.erb -->
<h1><%= @user.name %></h1>

<%= turbo_frame_tag "user_content" do %>
  <div class="tabs">
    <%= link_to "Posts", user_posts_path(@user), data: { turbo_frame: "user_content" } %>
    <%= link_to "Comments", user_comments_path(@user), data: { turbo_frame: "user_content" } %>
    <%= link_to "Settings", user_settings_path(@user), data: { turbo_frame: "user_content" } %>
  </div>
  
  <div class="content">
    <%= render @content %>
  </div>
<% end %>
```

### Modal/Dialog Navigation

```erb
<!-- app/views/posts/index.html.erb -->
<%= turbo_frame_tag "modal" %>

<%= link_to "New Post", new_post_path, data: { turbo_frame: "modal" } %>

<!-- app/views/posts/new.html.erb -->
<%= turbo_frame_tag "modal" do %>
  <dialog open>
    <h2>New Post</h2>
    <%= render "form", post: @post %>
  </dialog>
<% end %>

<!-- After successful creation, close modal -->
<!-- app/views/posts/create.turbo_stream.erb -->
<%= turbo_stream.update "modal", "" %>
<%= turbo_stream.append "posts", partial: "post", locals: { post: @post } %>
```

## Stream Actions Reference

### Standard Actions

```erb
<!-- Replace an element -->
<%= turbo_stream.replace "post_123", partial: "post", locals: { post: @post } %>

<!-- Append to a container -->
<%= turbo_stream.append "posts", partial: "post", locals: { post: @post } %>

<!-- Prepend to a container -->
<%= turbo_stream.prepend "posts", partial: "post", locals: { post: @post } %>

<!-- Remove an element -->
<%= turbo_stream.remove "post_123" %>

<!-- Update content only (keeps element) -->
<%= turbo_stream.update "counter", @posts.count %>

<!-- Insert before/after -->
<%= turbo_stream.before "post_123", partial: "post", locals: { post: @new_post } %>
<%= turbo_stream.after "post_123", partial: "post", locals: { post: @new_post } %>
```

### Custom Actions

```javascript
// app/javascript/turbo_stream_actions.js
Turbo.StreamActions.highlight = function() {
  this.targetElements.forEach((element) => {
    element.classList.add("highlight")
    setTimeout(() => element.classList.remove("highlight"), 2000)
  })
}

Turbo.StreamActions.scroll_into_view = function() {
  this.targetElements.forEach((element) => {
    element.scrollIntoView({ behavior: "smooth", block: "center" })
  })
}
```

```erb
<%= turbo_stream.highlight "post_123" %>
<%= turbo_stream.scroll_into_view "post_123" %>
```

## Anti-patterns

### Broadcasting Order

```ruby
# ❌ Bad: Broadcasting before save
Turbo::StreamsChannel.broadcast_append_to("posts", partial: "post", locals: { post: @post })
@post.save  # Might fail after broadcast

# ✅ Good: Broadcast after successful save
if @post.save
  Turbo::StreamsChannel.broadcast_append_to("posts", partial: "post", locals: { post: @post })
end
```

### Double Subscriptions

```ruby
# ❌ Bad: Duplicate subscriptions
class Post < ApplicationRecord
  after_create_commit :notify_following_users
  
  private
  
  def notify_following_users
    user.followers.each do |follower|
      # User subscribes to "posts" AND [user, :feed]
      # Post broadcasts to both - duplicates!
      Turbo::StreamsChannel.broadcast_prepend_to(
        [follower, :feed], 
        target: "feed",
        partial: "posts/post",
        locals: { post: self }
      )
    end
    
    # Also broadcasts to "posts" stream
    broadcast_prepend_to "posts"  # Duplicate!
  end
end

# ✅ Good: Single broadcast per stream
class Post < ApplicationRecord
  after_create_commit :broadcast_to_feeds
  
  private
  
  def broadcast_to_feeds
    # User's personal feed
    broadcast_prepend_to [user, :feed], target: "feed"
    
    # Public feed (only if public)
    broadcast_prepend_to "posts" if public?
  end
end
```

### Missing Frame Targets

```erb
<!-- ❌ Bad: No target for turbo_stream.append -->
<div id="posts">
  <!-- Posts rendered here -->
</div>

<!-- ✅ Good: Empty container for appends -->
<div id="posts">
  <%= render @posts %>
</div>

<!-- Or for new empty list -->
<div id="posts"></div>
```

## Best Practices

### Use DOM IDs

```ruby
# app/helpers/application_helper.rb
def dom_id(record, prefix = nil)
  "#{prefix}#{record.class.name.underscore}_#{record.id}"
end

# Usage in views
turbo_frame_tag dom_id(post)              # => <turbo-frame id="post_123">
turbo_frame_tag dom_id(post, :edit)     # => <turbo-frame id="edit_post_123">
```

### Broadcast Efficiently

```ruby
# ❌ Bad: Render partial for each follower (N renders)
user.followers.each do |follower|
  Turbo::StreamsChannel.broadcast_prepend_to(
    [follower, :feed],
    target: "feed",
    partial: "posts/post",
    locals: { post: post }
  )
end

# ✅ Good: Render once, broadcast to all
html = ApplicationController.render(
  partial: "posts/post",
  locals: { post: post }
)

user.followers.each do |follower|
  Turbo::StreamsChannel.broadcast_prepend_to(
    [follower, :feed],
    target: "feed",
    html: html
  )
end
```

### Testing Streams

```ruby
# spec/requests/posts_spec.rb
RSpec.describe "Posts", type: :request do
  it "broadcasts to posts stream on creation" do
    expect {
      post posts_path, params: { post: attributes_for(:post) }
    }.to have_broadcasted_to("posts")
     .with(a_string_matching(/turbo-stream/))
  end
end

# spec/system/turbo_streams_spec.rb
RSpec.describe "Turbo Streams", type: :system do
  it "updates page in real-time", js: true do
    visit posts_path
    
    # Create post in another session
    using_session(:other_user) do
      Post.create!(title: "New Post", body: "Content")
    end
    
    # Post appears on current page without refresh
    expect(page).to have_content("New Post")
  end
end
```
