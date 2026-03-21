# JavaScript Interoperability Reference

Rails with Turbo uses morphdom for DOM patching. Third-party JS libraries that manage their own DOM state can conflict with this. This reference covers resolution patterns.

## Contents

- [The Core Problem](#the-core-problem)
- [Solution 1: data-turbo-permanent](#solution-1-data-turbo-permanent)
- [Solution 2: Stimulus Controllers](#solution-2-stimulus-controllers-with-lifecycle)
- [Solution 3: Server-Driven Updates via fetch](#solution-3-server-driven-updates-via-custom-events)
- [Common Library Patterns](#common-library-patterns)
- [Anti-Patterns](#anti-patterns)
- [Decision Tree](#decision-tree)
- [Multi-Locale DOM Safety](#multi-locale-dom-safety)

## The Core Problem

```
Rails Server + Turbo                    Browser DOM
      │                                  │
      │  sends HTML diff ──────────────►  │
      │                                  │
      │                            morphdom patches
      │                                  │
      │                            ✗ DESTROYS JS state
      │                            ✗ TipTap loses content
      │                            ✗ Chart.js resets
```

## Solution 1: data-turbo-permanent

Tell Turbo to skip DOM diffing for a subtree.

```erb
<div id="editor-wrapper" data-controller="tiptap">
  <div id="editor-content" data-turbo-permanent>
    <!-- JS library manages everything inside here -->
    <!-- Turbo will NEVER touch this subtree -->
  </div>
</div>
```

### Rules

1. **Must have unique ID** - Required for morphdom tracking
2. **Initial content preserved** - Whatever is rendered on mount stays
3. **No Turbo updates** - DOM changes won't affect this element
4. **Stimulus still works** - Controller can manage initialization

### When to Use

| Library Type | Use data-turbo-permanent? |
|--------------|---------------------------|
| Rich text editors (TipTap, Quill, ProseMirror) | Yes |
| Charts (Chart.js, D3, Plotly) | Yes |
| Maps (Leaflet, Mapbox, Google Maps) | Yes |
| Date pickers (Flatpickr) | Yes |
| Alpine.js components | Sometimes |
| Simple JS animations | Usually not needed |

## Solution 2: Stimulus Controllers with Lifecycle

```javascript
// app/javascript/controllers/tiptap_editor_controller.js
import { Controller } from "@hotwired/stimulus"
import { Editor } from "@tiptap/core"

export default class extends Controller {
  static targets = ["content"]
  static values = {
    initialContent: String
  }

  connect() {
    // Initialize when element enters DOM
    this.editor = new Editor({
      element: this.contentTarget,
      content: this.initialContentValue || '',
      onUpdate: ({ editor }) => {
        // Send changes to server
        this.sendUpdate(editor.getHTML())
      }
    })
  }

  disconnect() {
    // Cleanup when element leaves DOM
    this.editor?.destroy()
  }

  // Receives updates from server via Turbo Streams
  updateContent({ detail: { content } }) {
    this.editor.commands.setContent(content, false)
  }

  sendUpdate(content) {
    // Send to server via fetch or Turbo Stream
    fetch('/api/content/update', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': document.querySelector('[name="csrf-token"]').content
      },
      body: JSON.stringify({ content })
    })
  }
}
```

### Controller Registration

```javascript
// app/javascript/controllers/index.js
import { application } from "./application"
import TiptapEditorController from "./tiptap_editor_controller"
import ChartController from "./chart_controller"

application.register("tiptap-editor", TiptapEditorController)
application.register("chart", ChartController)
```

### ERB Template

```erb
<div
  id="editor-<%= @post.id %>"
  data-controller="tiptap-editor"
  data-tiptap-editor-initial-content-value="<%= @post.content %>"
  data-action="tiptap:update@document->tiptap-editor#updateContent"
>
  <div data-tiptap-editor-target="content" data-turbo-permanent></div>
</div>
```

## Solution 3: Server-Driven Updates via Custom Events

When server needs to update JS state without DOM patching:

### Controller

```ruby
# app/controllers/posts_controller.rb
def update_content
  @post = Post.find(params[:id])
  
  if @post.update(content_params)
    # Broadcast to all subscribers via Turbo Stream
    Turbo::StreamsChannel.broadcast_replace_to(
      @post,
      target: "post-#{@post.id}",
      partial: "posts/post",
      locals: { post: @post }
    )
    
    # Also send custom event for JS libraries
    Turbo::StreamsChannel.broadcast_action_to(
      @post,
      action: :custom,
      target: "post-#{@post.id}",
      attributes: { 
        "data-tiptap-content" => @post.content 
      }
    )
    
    head :ok
  else
    render json: { errors: @post.errors }, status: :unprocessable_entity
  end
end
```

### JavaScript with Custom Event

```javascript
// Listen for custom Turbo Stream events
document.addEventListener('turbo:frame-load', (event) => {
  const frame = event.target
  const content = frame.dataset.tiptapContent
  
  if (content && window.tiptapEditor) {
    window.tiptapEditor.commands.setContent(content, false)
  }
})

// Or using Stimulus action on the element
data-action="turbo:frame-load->tiptap-editor#syncContent"
```

## Common Library Patterns

### Chart.js

```erb
<div
  id="chart-<%= @chart_id %>"
  data-controller="chart"
  data-chart-type-value="<%= @chart_type %>"
  data-chart-datasets-value="<%= @datasets.to_json %>"
>
  <canvas data-turbo-permanent></canvas>
</div>
```

```javascript
// app/javascript/controllers/chart_controller.js
import { Controller } from "@hotwired/stimulus"
import { Chart } from "chart.js"

export default class extends Controller {
  static targets = ["canvas"]
  static values = {
    type: String,
    datasets: Array
  }

  connect() {
    this.chart = new Chart(this.canvasTarget, {
      type: this.typeValue,
      data: { datasets: this.datasetsValue }
    })
  }

  disconnect() {
    this.chart?.destroy()
  }

  update({ detail: { datasets } }) {
    this.chart.data = datasets
    this.chart.update()
  }
}
```

### Leaflet Maps

```erb
<div
  id="map-container"
  data-controller="map"
  data-map-lat-value="<%= @center.lat %>"
  data-map-lng-value="<%= @center.lng %>"
>
  <div id="map" data-turbo-permanent style="height: 400px;"></div>
</div>
```

```javascript
// app/javascript/controllers/map_controller.js
import { Controller } from "@hotwired/stimulus"
import L from "leaflet"

export default class extends Controller {
  static values = {
    lat: Number,
    lng: Number
  }

  connect() {
    this.map = L.map('map').setView([this.latValue, this.lngValue], 13)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png').addTo(this.map)
  }

  disconnect() {
    this.map?.remove()
  }
}
```

### Alpine.js

```erb
<%# Option 1: data-turbo-permanent for Alpine-only sections %>
<div id="dropdown" data-turbo-permanent x-data="{ open: false }">
  <button @click="open = !open">Toggle</button>
  <div x-show="open">Content</div>
</div>

<%# Option 2: Alpine for UI state, Turbo for data %>
<div x-data="{ expanded: false }">
  <button @click="expanded = !expanded"><%= @item.title %></button>
  <div x-show="expanded">
    <%# Turbo can update this content %>
    <%= @item.description %>
  </div>
</div>
```

## Anti-Patterns

### Forget unique IDs

```erb
<%# BAD: No ID means morphdom can't track it %>
<div data-turbo-permanent><canvas></canvas></div>

<%# GOOD: Unique ID for tracking %>
<div id="chart-1" data-turbo-permanent><canvas></canvas></div>
```

### Put data-turbo-permanent on controller element

```erb
<%# BAD: Controller loses connect/disconnect callbacks %>
<div id="editor" data-controller="tiptap" data-turbo-permanent></div>

<%# GOOD: Separate controller from permanent content %>
<div id="editor" data-controller="tiptap">
  <div id="editor-content" data-turbo-permanent></div>
</div>
```

### Forget cleanup in disconnect

```javascript
// BAD: Memory leak
export default class extends Controller {
  connect() {
    this.chart = new Chart(...)
  }
}

// GOOD: Proper cleanup
export default class extends Controller {
  connect() {
    this.chart = new Chart(...)
  }
  
  disconnect() {
    this.chart?.destroy()
  }
}
```

### Use instance variables for JS-managed content

```ruby
# BAD: Turbo tries to update, conflicts with JS
def update
  @content = params[:content]
  render turbo_stream: turbo_stream.replace(@post, partial: "post")
end

# GOOD: Send custom event for JS, render for others
def update
  Turbo::StreamsChannel.broadcast_action_to(
    @post,
    action: :custom,
    target: "post-#{@post.id}",
    attributes: { "data-content" => params[:content] }
  )
end
```

## Decision Tree

```
Is your JS library managing DOM state?
│
├─ NO → Normal Turbo, no special handling
│
└─ YES → Does Turbo need to update that DOM area?
         │
         ├─ NO → Use data-turbo-permanent
         │       JS owns it completely
         │
         └─ YES → Use Stimulus Controller
                  Server sends events, JS updates itself
```

## Multi-Locale DOM Safety

Translated text can change DOM structure (different word count, RTL, different element wrapping). JS that relies on DOM position breaks across locales.

### Rules

1. **NEVER use positional selectors** (`children[0]`, `firstChild`, `nth-child`) in JS
2. **ALWAYS use `querySelector` with `data-*` attributes** for stable element targeting
3. **Test with longest locale** — German/Finnish strings are often 30-50% longer than English

### Anti-Pattern

```javascript
// BAD: Position changes when translation adds/removes elements
connect() {
  this.target = this.element.children[0]
  this.label = this.element.querySelector('span:first-child')
}
```

### Correct Pattern

```javascript
// GOOD: data attributes survive translation changes
connect() {
  this.target = this.element.querySelector('[data-role="content"]')
  this.label = this.element.querySelector('[data-role="label"]')
}
```

```erb
<div id="my-component" data-controller="my-component">
  <span data-role="label"><%= t("status") %></span>
  <div data-role="content"><%= @content %></div>
</div>
```
