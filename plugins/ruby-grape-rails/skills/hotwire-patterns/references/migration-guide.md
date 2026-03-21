## Migration from Rails UJS

| Rails UJS | Turbo/Hotwire |
|-----------|---------------|
| `data-remote="true"` | Automatic with Turbo Drive |
| `data-method="delete"` | `data-turbo-method="delete"` |
| `data-confirm="Sure?"` | `data-turbo-confirm="Sure?"` |
| `$.ajax` | `fetch()` or Turbo Forms |
| Turbolinks | Turbo Drive |
| Rails.ajax | Stimulus + fetch |

```javascript
// Remove from application.js
// require('@rails/ujs').start()

// Keep these if using them
// require('@rails/activestorage').start()
// require('@rails/actioncable').start()
```

```erb
<!-- UJS -->
<%= link_to "Delete", post_path(@post), 
            method: :delete, 
            data: { confirm: "Are you sure?" } %>

<!-- Turbo -->
<%= link_to "Delete", post_path(@post), 
            data: { 
              turbo_method: :delete,
              turbo_confirm: "Are you sure?" 
            } %>
```
