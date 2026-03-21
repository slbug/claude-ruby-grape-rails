## Real-time Features with Turbo

### Notifications

```ruby
# app/models/notification.rb
class Notification < ApplicationRecord
  belongs_to :user
  
  after_create_commit -> { 
    broadcast_prepend_to [user, "notifications"],
                         target: "notifications",
                         partial: "notifications/notification"
  }
end
```

```erb
<!-- app/views/layouts/_header.html.erb -->
<div data-controller="notifications">
  <%= turbo_stream_from current_user, "notifications" %>
  
  <button data-action="click->notifications#toggle">
    🔔 <span id="notification_count"><%= current_user.notifications.unread.count %></span>
  </button>
  
  <div id="notifications" class="hidden">
    <%= render current_user.notifications.recent %>
  </div>
</div>
```

```ruby
# app/controllers/notifications_controller.rb
class NotificationsController < ApplicationController
  def mark_read
    current_user.notifications.unread.update_all(read_at: Time.current)
    
    respond_to do |format|
      format.turbo_stream do
        render turbo_stream: turbo_stream.update("notification_count", 0)
      end
    end
  end
end
```

### Live Search

```erb
<!-- app/views/products/index.html.erb -->
<%= form_with url: products_path, 
              method: :get,
              data: { 
                controller: "search",
                turbo_frame: "products",
                turbo_action: "advance"
              } do |f| %>
  <%= f.text_field :query,
                   placeholder: "Search products...",
                   data: { action: "input->search#submit" } %>
<% end %>

<%= turbo_frame_tag "products" do %>
  <%= render @products %>
<% end %>
```

```javascript
// app/javascript/controllers/search_controller.js
import { Controller } from '@hotwired/stimulus'

export default class extends Controller {
  submit() {
    clearTimeout(this.timeout)
    this.timeout = setTimeout(() => {
      this.element.requestSubmit()
    }, 200)
  }
}
```

```ruby
# app/controllers/products_controller.rb
def index
  @products = Product.search(params[:query]).page(params[:page])
  
  respond_to do |format|
    format.html
    format.turbo_stream
  end
end
```
