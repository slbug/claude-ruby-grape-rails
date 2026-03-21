## Anti-patterns

```ruby
# ❌ Don't duplicate state between DOM and Stimulus
<div data-controller="counter"
     data-counter-count-value="<%= @count %>">
  <span data-counter-target="display"><%= @count %></span>
</div>

# ✅ Source of truth is server, DOM reflects it
<div data-controller="counter">
  <span data-counter-target="display"><%= @count %></span>
</div>

# ❌ Don't use Stimulus for complex business logic
export default class extends Controller {
  checkout() {
    // Calculating totals, taxes, shipping - belongs server-side
  }
}

# ✅ Submit to server, let it calculate and return updates
export default class extends Controller {
  async checkout() {
    const response = await fetch('/checkout', {
      method: 'POST',
      body: new FormData(this.formTarget)
    })
    Turbo.renderStreamMessage(await response.text())
  }
}

# ❌ Don't broadcast before commit
class Comment < ApplicationRecord
  after_create :broadcast  # Dangerous if transaction rolls back!
  
  private
  
  def broadcast
    broadcast_prepend_to "comments"
  end
end

# ✅ Always use after_create_commit
class Comment < ApplicationRecord
  after_create_commit -> { broadcast_prepend_to "comments" }
end

# ❌ Don't over-use Action Cable when Turbo Streams suffice
# (For most CRUD operations, Turbo Streams are simpler)

# ✅ Use Action Cable for:
# - Real-time collaborative editing
# - Chat applications
# - Live game state
# - High-frequency updates
```
