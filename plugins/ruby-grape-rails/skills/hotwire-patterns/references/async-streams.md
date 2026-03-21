# Turbo Frames and Lazy Loading Reference

## Lazy Loading with Turbo Frames

Turbo Frames support lazy loading out of the box, loading content when the frame becomes visible or on demand.

```erb
<!-- Lazy load when frame enters viewport -->
<%= turbo_frame_tag "user_stats", src: user_stats_path(@user), loading: :lazy do %>
  <p>Loading stats...</p>
<% end %>

<!-- Eager load immediately -->
<%= turbo_frame_tag "comments", src: post_comments_path(@post) do %>
  <p>Loading comments...</p>
<% end %>
```

### Loading States

```erb
<!-- app/views/users/_stats.html.erb -->
<%= turbo_frame_tag "user_stats" do %>
  <div class="stats">
    <h3>User Statistics</h3>
    <p>Posts: <%= @stats.posts_count %></p>
    <p>Comments: <%= @stats.comments_count %></p>
  </div>
<% end %>
```

## Infinite Scroll with Turbo Streams

### Controller

```ruby
# app/controllers/posts_controller.rb
class PostsController < ApplicationController
  def index
    @posts = Post.order(created_at: :desc).page(params[:page]).per(20)
    
    respond_to do |format|
      format.html
      format.turbo_stream do
        render turbo_stream: [
          turbo_stream.append("posts", partial: "posts/post", collection: @posts),
          turbo_stream.replace("load_more", partial: "posts/load_more", locals: { page: @posts.next_page })
        ]
      end
    end
  end
end
```

### Load More Button

```erb
<!-- app/views/posts/index.html.erb -->
<div id="posts">
  <%= render @posts %>
</div>

<%= turbo_frame_tag "load_more" do %>
  <% if @posts.next_page %>
    <%= link_to "Load More", posts_path(page: @posts.next_page), 
        data: { turbo_stream: true }, 
        class: "btn btn-primary" %>
  <% end %>
<% end %>
```

### Auto-Loading with Intersection Observer

```javascript
// app/javascript/controllers/infinite_scroll_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["trigger"]
  static values = {
    nextPage: String
  }

  connect() {
    this.observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && this.nextPageValue) {
          this.loadMore()
        }
      })
    })
    
    this.observer.observe(this.triggerTarget)
  }

  disconnect() {
    this.observer?.disconnect()
  }

  loadMore() {
    if (this.loading) return
    this.loading = true
    
    fetch(this.nextPageValue, {
      headers: { "Accept": "text/vnd.turbo-stream.html" }
    })
    .then(response => response.text())
    .then(html => Turbo.renderStreamMessage(html))
    .finally(() => {
      this.loading = false
    })
  }
}
```

```erb
<div id="posts">
  <%= render @posts %>
</div>

<div 
  data-controller="infinite-scroll"
  data-infinite-scroll-next-page-value="<%= posts_path(page: @posts.next_page) %>"
>
  <div data-infinite-scroll-target="trigger" class="loading-spinner">
    Loading more...
  </div>
</div>
```

## Background Jobs with Turbo Streams

### Triggering and Polling

```ruby
# app/controllers/exports_controller.rb
def create
  @export = current_user.exports.create!(export_params)
  ExportJob.perform_later(@export)
  
  redirect_to export_path(@export)
end

def show
  @export = current_user.exports.find(params[:id])
end
```

```erb
<!-- app/views/exports/show.html.erb -->
<%= turbo_stream_from @export %>

<%= turbo_frame_tag "export_status" do %>
  <% if @export.completed? %>
    <%= link_to "Download", rails_blob_path(@export.file, disposition: "attachment") %>
  <% elsif @export.failed? %>
    <p class="error">Export failed: <%= @export.error_message %></p>
  <% else %>
    <p>Processing... <%= @export.progress %>%</p>
    <progress value="<%= @export.progress %>" max="100"></progress>
  <% end %>
<% end %>
```

### Job Broadcasting Progress

```ruby
# app/jobs/export_job.rb
class ExportJob < ApplicationJob
  def perform(export)
    total = export.record_count
    
    export.record_ids.each_with_index do |id, index|
      process_record(id)
      
      # Broadcast progress every 10 records
      if index % 10 == 0
        export.update!(progress: (index + 1) * 100 / total)
        
        Turbo::StreamsChannel.broadcast_replace_to(
          export,
          target: "export_status",
          partial: "exports/status",
          locals: { export: export }
        )
      end
    end
    
    export.update!(status: :completed, completed_at: Time.current)
    
    Turbo::StreamsChannel.broadcast_replace_to(
      export,
      target: "export_status",
      partial: "exports/status",
      locals: { export: export }
    )
  end
end
```

## Debouncing Form Submissions

### Stimulus Controller

```javascript
// app/javascript/controllers/form_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["submit"]

  connect() {
    this.submitHandler = this.debounce(this.submit.bind(this), 300)
  }

  submit(event) {
    // Form will submit normally via Turbo
    this.submitTarget.disabled = true
    this.submitTarget.textContent = "Submitting..."
  }

  debounce(func, wait) {
    let timeout
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout)
        func(...args)
      }
      clearTimeout(timeout)
      timeout = setTimeout(later, wait)
    }
  }
}
```

```erb
<%= form_with model: @search, data: { controller: "form" } do |f| %>
  <%= f.text_field :query, 
      data: { action: "input->form#submitHandler" } %>
  <%= f.submit "Search", data: { form_target: "submit" } %>
<% end %>
```

## Real-time Search with Debounce

```javascript
// app/javascript/controllers/search_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["input", "results"]

  connect() {
    this.debouncedSearch = this.debounce(this.performSearch.bind(this), 300)
  }

  search() {
    this.debouncedSearch()
  }

  async performSearch() {
    const query = this.inputTarget.value
    if (query.length < 2) return
    
    this.resultsTarget.innerHTML = "Searching..."
    
    const response = await fetch(`/search?q=${encodeURIComponent(query)}`, {
      headers: { "Accept": "text/vnd.turbo-stream.html" }
    })
    
    const html = await response.text()
    Turbo.renderStreamMessage(html)
  }

  debounce(func, wait) {
    let timeout
    return (...args) => {
      clearTimeout(timeout)
      timeout = setTimeout(() => func(...args), wait)
    }
  }
}
```

```erb
<div data-controller="search">
  <%= text_field_tag :q, nil, 
      data: { 
        search_target: "input",
        action: "input->search#search"
      },
      placeholder: "Search..." %>
  
  <div id="search_results" data-search-target="results">
    <!-- Results loaded via Turbo Stream -->
  </div>
</div>
```

```ruby
# app/controllers/searches_controller.rb
def index
  @results = SearchService.search(params[:q]) if params[:q].present?
  
  respond_to do |format|
    format.turbo_stream do
      render turbo_stream: turbo_stream.update(
        "search_results",
        partial: "search/results",
        locals: { results: @results }
      )
    end
  end
end
```

## Anti-patterns

### Loading Data on Every Request

```ruby
# BAD: No caching, slow queries
class PostsController < ApplicationController
  def index
    @posts = Post.all.includes(:comments, :author) # Slow every time
  end
end

# GOOD: Use Russian Doll caching
class PostsController < ApplicationController
  def index
    @posts = Post.includes(:comments, :author).cache_tag_with(Post.maximum(:updated_at))
  end
end
```

```erb
<%# app/views/posts/index.html.erb %>
<%= turbo_frame_tag "posts" do %>
  <% @posts.each do |post| %>
    <%= render partial: "post", locals: { post: post } %>
  <% end %>
<% end %>

<%# app/views/posts/_post.html.erb %>
<% cache post do %>
  <article id="<%= dom_id(post) %>">
    <h2><%= post.title %></h2>
    <p><%= post.body %></p>
    <% cache [post, "comments"] do %>
      <%= render post.comments %>
    <% end %>
  </article>
<% end %>
```

### Not Handling Loading States

```erb
<%# BAD: No feedback while loading %>
<%= turbo_frame_tag "comments", src: post_comments_path(@post) %>

<%# GOOD: Show loading indicator %>
<%= turbo_frame_tag "comments", src: post_comments_path(@post), loading: :lazy do %>
  <div class="loading">
    <%= spinner_icon %>
    <span>Loading comments...</span>
  </div>
<% end %>
```

### Synchronous Heavy Operations

```ruby
# BAD: Blocks request
class ReportsController < ApplicationController
  def create
    @report = Report.generate(params) # Takes 30 seconds
    send_data @report.to_csv
  end
end

# GOOD: Background job with Turbo Stream updates
class ReportsController < ApplicationController
  def create
    @report = current_user.reports.create!(status: :pending)
    ReportGenerationJob.perform_later(@report, params)
    redirect_to report_path(@report)
  end
end
```

## Best Practices

### Use Lazy Loading for Secondary Content

```erb
<!-- Primary content loads immediately -->
<div class="main-content">
  <%= render @post %>
</div>

<!-- Secondary content lazy loaded -->
<%= turbo_frame_tag "related_posts", src: related_posts_path(@post), loading: :lazy do %>
  <p>Loading related posts...</p>
<% end %>

<%= turbo_frame_tag "comments", src: post_comments_path(@post), loading: :lazy do %>
  <p>Loading comments...</p>
<% end %>
```

### Cache Expensive Frames

```ruby
# app/helpers/turbo_helper.rb
module TurboHelper
  def cached_turbo_frame_tag(name, src:, **options, &block)
    cache([name, src], expires_in: 5.minutes) do
      turbo_frame_tag(name, src: src, **options, &block)
    end
  end
end
```

### Graceful Degradation

```erb
<%# Works without JavaScript %>
<%= turbo_frame_tag "posts" do %>
  <%= render @posts %>
  <%= link_to "Next page", posts_path(page: 2), 
      data: { turbo_frame: "posts" },
      class: "turbo-only" %>
<% end %>
```

```css
/* Hide Turbo-only elements when JS is disabled */
.no-js .turbo-only {
  display: none;
}
```
