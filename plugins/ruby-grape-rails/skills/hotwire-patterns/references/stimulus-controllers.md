## Stimulus Controllers

### Basic Structure

```javascript
// app/javascript/controllers/hello_controller.js
import { Controller } from '@hotwired/stimulus'

export default class extends Controller {
  static targets = ['name', 'output']
  static values = {
    url: String,
    interval: { type: Number, default: 5000 }
  }
  
  connect() {
    console.log('Hello controller connected')
    this.startPolling()
  }
  
  disconnect() {
    this.stopPolling()
  }
  
  greet() {
    this.outputTarget.textContent = `Hello, ${this.nameTarget.value}!`
  }
  
  // Actions
  async refresh() {
    const response = await fetch(this.urlValue)
    const html = await response.text()
    this.element.innerHTML = html
  }
  
  // Private methods
  startPolling() {
    this.pollInterval = setInterval(() => this.refresh(), this.intervalValue)
  }
  
  stopPolling() {
    clearInterval(this.pollInterval)
  }
}
```

```erb
<!-- app/views/posts/show.html.erb -->
<div data-controller="hello"
     data-hello-url-value="<%= post_path(@post, format: :turbo_stream) %>"
     data-hello-interval-value="10000">
  
  <input type="text" data-hello-target="name">
  <button data-action="click->hello#greet">Greet</button>
  
  <div data-hello-target="output"></div>
</div>
```

### Common Patterns

#### Toggle Visibility

```javascript
// app/javascript/controllers/toggle_controller.js
import { Controller } from '@hotwired/stimulus'

export default class extends Controller {
  static targets = ['content']
  static classes = ['hidden']
  
  toggle() {
    this.contentTarget.classList.toggle(this.hiddenClass)
  }
  
  show() {
    this.contentTarget.classList.remove(this.hiddenClass)
  }
  
  hide() {
    this.contentTarget.classList.add(this.hiddenClass)
  }
}
```

```erb
<div data-controller="toggle" data-toggle-hidden-class="hidden">
  <button data-action="click->toggle#toggle">Toggle Details</button>
  <div data-toggle-target="content" class="hidden">
    Hidden content here
  </div>
</div>
```

#### Auto-submit Form

```javascript
// app/javascript/controllers/auto_submit_controller.js
import { Controller } from '@hotwired/stimulus'

export default class extends Controller {
  static targets = ['form']
  static values = {
    delay: { type: Number, default: 300 }
  }
  
  connect() {
    this.timeout = null
  }
  
  submit() {
    clearTimeout(this.timeout)
    this.timeout = setTimeout(() => {
      this.formTarget.requestSubmit()
    }, this.delayValue)
  }
}
```

```erb
<%= form_with model: @search, 
              data: { 
                controller: "auto-submit",
                auto_submit_target: "form"
              } do |f| %>
  <%= f.text_field :query, 
                   data: { action: "input->auto-submit#submit" } %>
<% end %>
```

#### Copy to Clipboard

```javascript
// app/javascript/controllers/clipboard_controller.js
import { Controller } from '@hotwired/stimulus'

export default class extends Controller {
  static targets = ['source', 'button']
  static values = {
    successText: { type: String, default: 'Copied!' }
  }
  
  async copy() {
    const text = this.sourceTarget.value || this.sourceTarget.textContent
    
    try {
      await navigator.clipboard.writeText(text)
      this.showFeedback()
    } catch (err) {
      console.error('Failed to copy:', err)
      this.fallbackCopy(text)
    }
  }
  
  showFeedback() {
    const originalText = this.buttonTarget.textContent
    this.buttonTarget.textContent = this.successTextValue
    
    setTimeout(() => {
      this.buttonTarget.textContent = originalText
    }, 2000)
  }
  
  fallbackCopy(text) {
    const input = document.createElement('input')
    input.value = text
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
  }
}
```

```erb
<div data-controller="clipboard">
  <input data-clipboard-target="source" 
         value="<%= @coupon.code %>" 
         readonly>
  <button data-action="click->clipboard#copy" 
          data-clipboard-target="button">
    Copy
  </button>
</div>
```

#### Remote Modal

```javascript
// app/javascript/controllers/modal_controller.js
import { Controller } from '@hotwired/stimulus'

export default class extends Controller {
  static targets = ['container', 'content']
  
  open(event) {
    const url = event.currentTarget.href
    
    fetch(url, {
      headers: { 'Accept': 'text/vnd.turbo-stream.html' }
    })
    .then(response => response.text())
    .then(html => {
      this.contentTarget.innerHTML = html
      this.containerTarget.classList.remove('hidden')
    })
  }
  
  close() {
    this.containerTarget.classList.add('hidden')
    this.contentTarget.innerHTML = ''
  }
  
  closeOnBackground(event) {
    if (event.target === this.containerTarget) {
      this.close()
    }
  }
}
```

```erb
<!-- app/views/shared/_modal.html.erb -->
<div data-controller="modal">
  <button data-action="click->modal#open" 
          href="<%= new_post_path %>">
    New Post
  </button>
  
  <div data-modal-target="container" 
       data-action="click->modal#closeOnBackground"
       class="hidden fixed inset-0 bg-black bg-opacity-50 z-50">
    <div class="bg-white p-6 rounded-lg max-w-2xl mx-auto mt-20">
      <button data-action="click->modal#close">&times;</button>
      <div data-modal-target="content"></div>
    </div>
  </div>
</div>
```

### Stimulus Best Practices

```javascript
// ✅ Good - Single responsibility
export default class extends Controller {
  static targets = ['input', 'counter']
  
  count() {
    const length = this.inputTarget.value.length
    this.counterTarget.textContent = `${length} characters`
  }
}

// ❌ Bad - Business logic in controller
export default class extends Controller {
  calculateTotal() {
    // Tax calculations, discounts, etc. - belongs in server-side code
    const subtotal = this.getSubtotal()
    const tax = subtotal * 0.08
    const total = subtotal + tax
    this.displayTotal(total)
  }
}

// ✅ Good - Keep server state as source of truth
export default class extends Controller {
  async updateQuantity(event) {
    const response = await fetch('/cart/update', {
      method: 'POST',
      body: new FormData(this.element)
    })
    
    // Let server calculate and return updated cart
    Turbo.renderStreamMessage(await response.text())
  }
}
```
