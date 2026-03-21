# View Components and Stimulus Reference

## View Components

View Components are Ruby classes that render views, providing better encapsulation than partials.

### Basic Component

```ruby
# app/components/button_component.rb
class ButtonComponent < ViewComponent::Base
  def initialize(variant: :primary, size: :medium, disabled: false)
    @variant = variant
    @size = size
    @disabled = disabled
  end
  
  private
  
  def css_classes
    [
      "btn",
      "btn-#{@variant}",
      "btn-#{@size}",
      ("btn-disabled" if @disabled)
    ].compact.join(" ")
  end
end

# app/components/button_component.html.erb
<button class="<%= css_classes %>" <%= "disabled" if @disabled %>>
  <%= content %>
</button>

# Usage in views
<%= render(ButtonComponent.new(variant: :secondary)) do %>
  Click me
<% end %>
```

### Component with Slots

```ruby
# app/components/card_component.rb
class CardComponent < ViewComponent::Base
  renders_one :header
  renders_one :body
  renders_many :actions
  
  def initialize(title: nil, class: nil)
    @title = title
    @class = binding.local_variable_get(:class)
  end
end

# app/components/card_component.html.erb
<div class="card <%= @class %>">
  <% if header %>
    <div class="card-header">
      <%= header %>
    </div>
  <% elsif @title %>
    <div class="card-header">
      <h3><%= @title %></h3>
    </div>
  <% end %>
  
  <div class="card-body">
    <%= body %>
  </div>
  
  <% if actions.any? %>
    <div class="card-actions">
      <% actions.each do |action| %>
        <%= action %>
      <% end %>
    </div>
  <% end %>
</div>

# Usage
<%= render(CardComponent.new(title: "User Profile")) do |component| %>
  <% component.with_body do %>
    <p>Name: <%= @user.name %></p>
    <p>Email: <%= @user.email %></p>
  <% end %>
  
  <% component.with_actions do %>
    <%= link_to "Edit", edit_user_path(@user), class: "btn" %>
  <% end %>
<% end %>
```

### Collection Components

```ruby
# app/components/user_row_component.rb
class UserRowComponent < ViewComponent::Base
  def initialize(user:)
    @user = user
  end
  
  def full_name
    "#{@user.first_name} #{@user.last_name}"
  end
end

# app/components/user_row_component.html.erb
<tr>
  <td><%= full_name %></td>
  <td><%= @user.email %></td>
  <td><%= @user.role %></td>
</tr>

# Usage in table
<%= render(UserRowComponent.with_collection(@users)) %>
```

## Stimulus Controllers

Stimulus is the JavaScript framework that pairs with Turbo, providing modest JavaScript behavior without SPA complexity.

### Basic Controller

```javascript
// app/javascript/controllers/hello_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["name", "output"]
  
  connect() {
    console.log("Hello controller connected")
  }
  
  greet() {
    const name = this.nameTarget.value
    this.outputTarget.textContent = `Hello, ${name}!`
  }
}
```

```erb
<!-- app/views/users/index.html.erb -->
<div data-controller="hello">
  <input data-hello-target="name" type="text" placeholder="Your name">
  <button data-action="click->hello#greet">Greet</button>
  <span data-hello-target="output"></span>
</div>
```

### Controller with Values

```javascript
// app/javascript/controllers/clipboard_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["source"]
  static values = {
    successMessage: String,
    errorMessage: String
  }
  
  connect() {
    if (!this.hasSuccessMessageValue) {
      this.successMessageValue = "Copied!"
    }
  }
  
  async copy() {
    try {
      await navigator.clipboard.writeText(this.sourceTarget.value)
      this.showFeedback(this.successMessageValue)
    } catch (err) {
      this.showFeedback(this.errorMessageValue || "Failed to copy")
    }
  }
  
  showFeedback(message) {
    // Show temporary feedback
    const original = this.element.textContent
    this.element.textContent = message
    setTimeout(() => {
      this.element.textContent = original
    }, 2000)
  }
}
```

```erb
<%= text_field_tag :url, request.url, readonly: true, 
      data: { controller: "clipboard", 
              clipboard_success_message_value: "URL copied!" } %>
<button data-action="clipboard#copy" data-clipboard-target="source">
  Copy Link
</button>
```

### Controller with Classes

```javascript
// app/javascript/controllers/toggle_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["content"]
  static classes = ["hidden", "visible"]
  
  toggle() {
    if (this.contentTarget.classList.contains(this.hiddenClass)) {
      this.contentTarget.classList.remove(this.hiddenClass)
      this.contentTarget.classList.add(this.visibleClass)
    } else {
      this.contentTarget.classList.remove(this.visibleClass)
      this.contentTarget.classList.add(this.hiddenClass)
    }
  }
}
```

```erb
<button data-controller="toggle" 
        data-toggle-target="content" 
        data-toggle-hidden-class="hidden"
        data-toggle-visible-class="block"
        data-action="click->toggle#toggle">
  Toggle
</button>

<div id="details" class="hidden" data-toggle-target="content">
  Hidden details here...
</div>
```

## Turbo Frame Patterns

### Lazy Loading

```erb
<!-- Frame loads content lazily -->
<%= turbo_frame_tag "user_stats", src: user_stats_path(@user), loading: :lazy do %>
  Loading stats...
<% end %>
```

### Frame Navigation

```erb
<!-- Current frame content -->
<%= turbo_frame_tag "user_form" do %>
  <%= form_with model: @user do |f| %>
    <%= f.text_field :name %>
    <%= f.submit "Update" %>
  <% end %>
  
  <!-- Link replaces this frame, not whole page -->
  <%= link_to "Change Password", edit_password_user_path(@user), 
      data: { turbo_frame: "user_form" } %>
<% end %>
```

## Turbo Streams from Controller

### Streaming Updates

```ruby
# app/controllers/posts_controller.rb
def destroy
  @post = Post.find(params[:id])
  @post.destroy
  
  respond_to do |format|
    format.html { redirect_to posts_path }
    format.turbo_stream do
      render turbo_stream: [
        turbo_stream.remove(@post),
        turbo_stream.update("post_count", Post.count),
        turbo_stream.prepend("notifications", 
          partial: "shared/notification", 
          locals: { message: "Post deleted" })
      ]
    end
  end
end
```

### Custom Stream Actions

```javascript
// app/javascript/controllers/turbo_stream_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["container"]
  
  // Custom stream action handler
  highlight({ target, detail }) {
    target.classList.add("highlight")
    setTimeout(() => {
      target.classList.remove("highlight")
    }, 2000)
  }
}
```

```erb
<div id="posts" data-controller="turbo-stream" data-turbo-stream-target="container">
  <%= render @posts %>
</div>
```

## Combining Stimulus and Turbo

```javascript
// app/javascript/controllers/form_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["submit", "error"]
  
  connect() {
    this.element.addEventListener("turbo:submit-start", this.handleSubmitStart)
    this.element.addEventListener("turbo:submit-end", this.handleSubmitEnd)
  }
  
  disconnect() {
    this.element.removeEventListener("turbo:submit-start", this.handleSubmitStart)
    this.element.removeEventListener("turbo:submit-end", this.handleSubmitEnd)
  }
  
  handleSubmitStart = () => {
    this.submitTarget.disabled = true
    this.submitTarget.textContent = "Saving..."
  }
  
  handleSubmitEnd = (event) => {
    this.submitTarget.disabled = false
    this.submitTarget.textContent = "Save"
    
    if (event.detail.success) {
      this.errorTarget.textContent = ""
    }
  }
}
```

```erb
<%= form_with model: @user, 
      data: { controller: "form", turbo: true } do |f| %>
  <%= f.text_field :name %>
  <span data-form-target="error" class="error"></span>
  
  <%= f.submit "Save", data: { form_target: "submit" } %>
<% end %>
```

## Best Practices

### Controller Organization

```javascript
// Keep controllers small and focused
// app/javascript/controllers/
//   ├── hello_controller.js
//   ├── clipboard_controller.js
//   ├── toggle_controller.js
//   ├── search_controller.js
//   └── modal_controller.js
```

### Data Attributes over IDs

```erb
<!-- Good: Uses data attributes -->
<div data-controller="dropdown" data-dropdown-open-value="false">
  <button data-action="click->dropdown#toggle">Menu</button>
  <div data-dropdown-target="menu" class="hidden">
    <%= link_to "Profile", profile_path %>
  </div>
</div>

<!-- Bad: Relies on IDs, not reusable -->
<div id="dropdown">
  <button onclick="toggleDropdown()">Menu</button>
</div>
```

### Progressive Enhancement

```erb
<!-- Works without JavaScript -->
<%= form_with model: @post do |f| %>
  <%= f.text_field :title %>
  
  <!-- Enhanced with Stimulus if JS available -->
  <div data-controller="autosave" data-autosave-delay-value="1000">
    <span data-autosave-target="status"></span>
  </div>
  
  <%= f.submit %>
<% end %>
```

## Testing Components

```ruby
# spec/components/button_component_spec.rb
require "rails_helper"

RSpec.describe ButtonComponent, type: :component do
  it "renders button with content" do
    render_inline(ButtonComponent.new) { "Click me" }
    
    expect(page).to have_css("button.btn", text: "Click me")
  end
  
  it "applies variant class" do
    render_inline(ButtonComponent.new(variant: :danger)) { "Delete" }
    
    expect(page).to have_css("button.btn-danger")
  end
end

# spec/system/stimulus_controller_spec.rb
RSpec.describe "Stimulus controllers", type: :system do
  it "toggles visibility" do
    visit toggle_demo_path
    
    expect(page).not_to have_text("Hidden content")
    
    click_button "Show"
    expect(page).to have_text("Hidden content")
    
    click_button "Hide"
    expect(page).not_to have_text("Hidden content")
  end
end
```
