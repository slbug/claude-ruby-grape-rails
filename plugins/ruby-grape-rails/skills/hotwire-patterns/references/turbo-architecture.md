## Turbo Architecture

### Turbo Drive

Turbo Drive handles page navigation without full page reloads:

```javascript
// app/javascript/application.js
import '@hotwired/turbo-rails'

// Turbo is automatic - no code needed for basic navigation
```

```erb
<!-- Disable Turbo for specific links -->
<%= link_to "External Link", "https://example.com", data: { turbo: false } %>

<!-- Disable Turbo for entire page -->
<head>
  <meta name="turbo-cache-control" content="no-cache">
</head>
```

### Turbo Frames

Scoped page updates without full navigation:

```erb
<!-- app/views/posts/index.html.erb -->
<h1>Posts</h1>

<%= turbo_frame_tag "posts" do %>
  <%= render @posts %>
<% end %>

<%= link_to "New Post", new_post_path, data: { turbo_frame: "posts" } %>
```

```erb
<!-- app/views/posts/new.html.erb -->
<%= turbo_frame_tag "posts" do %>
  <%= render "form", post: @post %>
<% end %>
```

```erb
<!-- app/views/posts/_post.html.erb -->
<%= turbo_frame_tag dom_id(post) do %>
  <article>
    <h2><%= post.title %></h2>
    <p><%= post.body %></p>
    <%= link_to "Edit", edit_post_path(post) %>
  </article>
<% end %>
```

#### Lazy Loading Frames

```erb
<!-- Load content asynchronously -->
<%= turbo_frame_tag "comments", src: post_comments_path(post), loading: "lazy" do %>
  <p>Loading comments...</p>
<% end %>
```

#### Frame Targets

```erb
<!-- Navigation targets specific frame -->
<%= link_to "Load Details", 
            post_path(post), 
            data: { turbo_frame: "post_details" } %>

<%= turbo_frame_tag "post_details" do %>
  <p>Select a post to see details</p>
<% end %>
```

### Turbo Streams

Server-driven DOM updates via WebSocket or HTTP:

```ruby
# app/controllers/posts_controller.rb
def create
  @post = Post.create(post_params)
  
  respond_to do |format|
    format.turbo_stream do
      render turbo_stream: [
        turbo_stream.prepend("posts", partial: "posts/post", locals: { post: @post }),
        turbo_stream.update("post_form", partial: "posts/form", locals: { post: Post.new }),
        turbo_stream.replace("flash", partial: "shared/flash")
      ]
    end
    format.html { redirect_to @post }
  end
end

def destroy
  @post.destroy
  
  respond_to do |format|
    format.turbo_stream do
      render turbo_stream: turbo_stream.remove(@post)
    end
    format.html { redirect_to posts_path }
  end
end
```

```erb
<!-- app/views/posts/create.turbo_stream.erb -->
<%= turbo_stream.prepend "posts" do %>
  <%= render @post %>
<% end %>

<%= turbo_stream.replace "flash" do %>
  <%= render "shared/flash", message: "Post created!" %>
<% end %>
```

#### Stream Actions Reference

```ruby
# Append to container
turbo_stream.append("posts", partial: "post", locals: { post: @post })

# Prepend to container
turbo_stream.prepend("posts", partial: "post", locals: { post: @post })

# Replace element
turbo_stream.replace(@post, partial: "posts/post", locals: { post: @post })

# Update element content (preserves element)
turbo_stream.update("post_count", Post.count)

# Remove element
turbo_stream.remove(@post)

# Insert before/after
turbo_stream.before("featured_post", partial: "post", locals: { post: @post })
turbo_stream.after("featured_post", partial: "post", locals: { post: @post })
```

### Turbo Streams from Model Broadcasts

```ruby
# app/models/post.rb
class Post < ApplicationRecord
  after_create_commit -> { broadcast_prepend_to "posts" }
  after_update_commit -> { broadcast_replace_to "posts" }
  after_destroy_commit -> { broadcast_remove_to "posts" }
  
  # Or shorthand for all three
  broadcasts_to ->(post) { "posts" }, inserts_by: :prepend
end
```

```erb
<!-- app/views/posts/index.html.erb -->
<%= turbo_stream_from "posts" %>

<div id="posts">
  <%= render @posts %>
</div>
```

#### Scoped Broadcasts

```ruby
# app/models/comment.rb
class Comment < ApplicationRecord
  belongs_to :post
  
  # Broadcast to specific post's stream
  after_create_commit -> { broadcast_append_to [post, "comments"] }
end
```

```erb
<!-- app/views/posts/show.html.erb -->
<%= turbo_stream_from @post, "comments" %>

<div id="comments">
  <%= render @post.comments %>
</div>
```

#### Broadcasting with Solid Cable

Rails 8 with Solid Cable (no Redis needed):

```ruby
# config/cable.yml
production:
  adapter: solid_cable
  connects_to:
    database:
      writing: cable
```

```bash
# Generate migrations
bin/rails solid_cable:install
```

Works identically to Redis - no code changes needed.
