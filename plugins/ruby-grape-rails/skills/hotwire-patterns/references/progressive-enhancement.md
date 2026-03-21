## Progressive Enhancement

```erb
<!-- Base functionality works without JavaScript -->
<%= form_with model: @post do |f| %>
  <%= f.text_field :title %>
  <%= f.text_area :body %>
  <%= f.submit %>
<% end %>

<!-- Enhanced with Turbo -->
<%= form_with model: @post, 
              data: { 
                controller: "form",
                action: "turbo:submit-start->form#disable turbo:submit-end->form#enable"
              } do |f| %>
  <%= f.text_field :title %>
  <%= f.text_area :body %>
  <%= f.submit data: { form_target: "submit" } %>
<% end %>
```

```javascript
// app/javascript/controllers/form_controller.js
export default class extends Controller {
  static targets = ['submit']
  
  disable() {
    this.submitTarget.disabled = true
    this.submitTarget.textContent = 'Saving...'
  }
  
  enable() {
    this.submitTarget.disabled = false
    this.submitTarget.textContent = 'Save'
  }
}
```
