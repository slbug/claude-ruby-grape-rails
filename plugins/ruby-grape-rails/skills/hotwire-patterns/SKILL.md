---
name: hotwire-patterns
description: Hotwire, Turbo, Stimulus, broadcasts, and server-rendered interaction patterns for Rails apps. Load for Turbo Frames, Turbo Streams, Stimulus controllers, Action Cable, and view update flows. Covers Rails 7+ and 8+ with modern Hotwire patterns.
user-invocable: false
effort: medium
---
# Hotwire Patterns

## Iron Laws

1. Keep server-rendered interactions simple before reaching for custom JS.
2. Broadcast after commit when Turbo Stream updates depend on committed state.
3. Keep Stimulus controllers focused on browser concerns, not business rules.
4. Avoid duplicating the same state in DOM, session, cache, and `Current` without a clear source of truth.
5. Use Turbo Frames for scoped navigation; Turbo Streams for server-driven updates.
6. Progressive enhancement: pages work without JavaScript, enhanced with it.

## Overview

Hotwire provides tools for building modern web applications with minimal JavaScript:

- **Turbo Drive** — Handles page navigation without full reloads
- **Turbo Frames** — Scoped page updates, independent navigation
- **Turbo Streams** — Server-driven page changes via WebSocket or HTTP
- **Stimulus** — JavaScript controllers for progressive enhancement

## Quick Decision Guide

| Use Case | Tool | Example |
|----------|------|---------|
| Page navigation | Turbo Drive | Click links, instant page loads |
| Modal/dialog | Turbo Frame | Login modal, settings panel |
| Independent scrollable area | Turbo Frame | Comments section, sidebar |
| Real-time updates | Turbo Streams | Notifications, live comments |
| Form validation | Stimulus | Character counter, date picker |
| Complex UI interaction | Stimulus | Drag and drop, autocomplete |

## Turbo Frames

```erb
<!-- Frame that updates independently -->
<%= turbo_frame_tag "comments" do %>
  <%= render @comments %>
<% end %>

<!-- Link targets specific frame -->
<%= link_to "Load more", comments_path(page: 2), data: { turbo_frame: "comments" } %>
```

See [Turbo Architecture](references/turbo-architecture.md) for Drive, Frames, and Streams.

## Turbo Streams

```erb
<!-- Broadcast from model -->
<%= turbo_stream_from @post %>

<!-- In view, streams update automatically -->
<%= turbo_frame_tag dom_id(@post) do %>
  <%= render @post %>
<% end %>
```

```ruby
# Controller action
class CommentsController < ApplicationController
  def create
    @comment = @post.comments.create!(comment_params)
    
    respond_to do |format|
      format.turbo_stream
      format.html { redirect_to @post }
    end
  end
end
```

See [Real-time Features](references/realtime-features.md) for broadcast patterns.

## Stimulus Controllers

```javascript
// app/javascript/controllers/clipboard_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["source", "button"]
  
  copy() {
    navigator.clipboard.writeText(this.sourceTarget.value)
    this.buttonTarget.textContent = "Copied!"
    
    setTimeout(() => {
      this.buttonTarget.textContent = "Copy"
    }, 2000)
  }
}
```

```erb
<!-- Usage -->
<div data-controller="clipboard">
  <input data-clipboard-target="source" value="Copy me!" readonly>
  <button data-clipboard-target="button" data-action="click->clipboard#copy">
    Copy
  </button>
</div>
```

See [Stimulus Controllers](references/stimulus-controllers.md) for patterns and best practices.

## Detailed Guides

- [Turbo Architecture](references/turbo-architecture.md) — Drive, Frames, Streams
- [Stimulus Controllers](references/stimulus-controllers.md) — Controller patterns
- [Progressive Enhancement](references/progressive-enhancement.md) — No-JS-first approach
- [Real-time Features](references/realtime-features.md) — Notifications, live updates
- [Testing](references/testing.md) — Testing Hotwire interactions
- [Anti-patterns](references/anti-patterns.md) — Common mistakes
- [Migration Guide](references/migration-guide.md) — From Rails UJS to Hotwire
- [Performance Tips](references/performance-tips.md) — Optimization strategies

## Key Patterns

### Frame + Stream Combo

```erb
<!-- Frame for navigation, stream for updates -->
<%= turbo_frame_tag "room" do %>
  <%= turbo_stream_from @room %>
  <div id="messages">
    <%= render @room.messages %>
  </div>
<% end %>
```

### Lazy Loading Frames

```erb
<%= turbo_frame_tag "stats", src: stats_path, loading: :lazy do %>
  <p>Loading stats...</p>
<% end %>
```

### Stimulus + Turbo Events

```javascript
// Reset form after Turbo submission
connect() {
  this.element.addEventListener("turbo:submit-end", () => {
    this.resetForm()
  })
}
```

## See Also

- [Hotwire Native](../hotwire-native/SKILL.md) — Mobile app patterns
- [Rails Contexts](../rails-contexts/SKILL.md) — Controllers and routing
- [Request State Audit](../request-state-audit/SKILL.md) — Audit state management
