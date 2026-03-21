# Forms and Uploads Reference

## Rails Form Handling

### Simple Form with Turbo

```ruby
# app/controllers/users_controller.rb
class UsersController < ApplicationController
  def new
    @user = User.new
  end

  def create
    @user = User.new(user_params)

    if @user.save
      redirect_to @user, notice: "User created successfully"
    else
      render :new, status: :unprocessable_entity
    end
  end

  private

  def user_params
    params.require(:user).permit(:name, :email, :avatar)
  end
end
```

```erb
<!-- app/views/users/new.html.erb -->
<%= turbo_frame_tag "user_form" do %>
  <%= form_with model: @user, data: { turbo: true } do |f| %>
    <% if @user.errors.any? %>
      <div class="errors">
        <h2><%= pluralize(@user.errors.count, "error") %> prohibited this user from being saved:</h2>
        <ul>
          <% @user.errors.full_messages.each do |msg| %>
            <li><%= msg %></li>
          <% end %>
        </ul>
      </div>
    <% end %>

    <div class="field">
      <%= f.label :name %>
      <%= f.text_field :name %>
    </div>

    <div class="field">
      <%= f.label :email %>
      <%= f.email_field :email %>
    </div>

    <%= f.submit "Create User" %>
  <% end %>
<% end %>
```

### Inline Validation with Stimulus

```javascript
// app/javascript/controllers/form_validation_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["input", "error"]

  validate() {
    const input = this.inputTarget
    const error = this.errorTarget
    
    if (input.validity.valid) {
      error.textContent = ""
      input.classList.remove("invalid")
    } else {
      error.textContent = input.validationMessage
      input.classList.add("invalid")
    }
  }

  async validateServer() {
    const input = this.inputTarget
    const response = await fetch(`/validate/email?email=${encodeURIComponent(input.value)}`)
    const data = await response.json()
    
    if (!data.valid) {
      this.errorTarget.textContent = data.error
      input.classList.add("invalid")
    }
  }
}
```

```erb
<%= form_with model: @user do |f| %>
  <div data-controller="form-validation">
    <%= f.label :email %>
    <%= f.email_field :email, 
        data: { 
          form_validation_target: "input",
          action: "blur->form-validation#validateServer input->form-validation#validate"
        } %>
    <span data-form-validation-target="error" class="error"></span>
  </div>
<% end %>
```

## Debouncing & Throttling

```javascript
// app/javascript/controllers/debounce_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static values = {
    delay: Number
  }

  connect() {
    this.timeout = null
  }

  debounce(event) {
    clearTimeout(this.timeout)
    this.timeout = setTimeout(() => {
      this.element.requestSubmit()
    }, this.delayValue)
  }
}
```

```erb
<%= form_with model: @search, 
    data: { 
      controller: "debounce",
      debounce_delay_value: 500
    } do |f| %>
  <%= f.text_field :query,
      data: { action: "input->debounce#debounce" } %>
<% end %>
```

## Dynamic Nested Forms

### Using Cocoon Gem

```ruby
# Gemfile
gem 'cocoon'
```

```javascript
// app/javascript/application.js
import "@nathanvda/cocoon"
```

```erb
<%= form_with model: @order do |f| %>
  <%= f.text_field :customer_name %>
  
  <h3>Items</h3>
  <div id="items">
    <%= f.fields_for :items do |item_form| %>
      <%= render 'item_fields', f: item_form %>
    <% end %>
  </div>
  
  <%= link_to_add_association 'Add Item', f, :items,
      data: { 
        association_insertion_node: '#items',
        association_insertion_method: 'append'
      } %>
  
  <%= f.submit %>
<% end %>
```

```erb
<!-- app/views/orders/_item_fields.html.erb -->
<div class="nested-fields">
  <%= f.text_field :product_name %>
  <%= f.number_field :quantity %>
  <%= f.number_field :price, step: 0.01 %>
  <%= link_to_remove_association "Remove", f %>
</div>
```

### Vanilla Rails with Turbo

```erb
<%= form_with model: @order, data: { controller: "nested-form" } do |f| %>
  <template data-nested-form-target="template">
    <%= f.fields_for :items, Item.new, child_index: 'NEW_RECORD' do |item_fields| %>
      <%= render "item_fields", f: item_fields %>
    <% end %>
  </template>
  
  <div data-nested-form-target="container">
    <%= f.fields_for :items do |item_fields| %>
      <%= render "item_fields", f: item_fields %>
    <% end %>
  </div>
  
  <button type="button" data-action="nested-form#add">Add Item</button>
  <%= f.submit %>
<% end %>
```

```javascript
// app/javascript/controllers/nested_form_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["template", "container"]

  add(event) {
    event.preventDefault()
    
    const content = this.templateTarget.innerHTML.replace(/NEW_RECORD/g, new Date().getTime())
    this.containerTarget.insertAdjacentHTML('beforeend', content)
  }

  remove(event) {
    event.preventDefault()
    const wrapper = event.target.closest('.nested-fields')
    wrapper.querySelector("input[name*='_destroy']").value = "1"
    wrapper.style.display = 'none'
  }
}
```

## File Uploads with Active Storage

### Direct Uploads

```ruby
# app/models/user.rb
class User < ApplicationRecord
  has_one_attached :avatar
  
  validates :avatar, content_type: ['image/png', 'image/jpg', 'image/jpeg'],
                     size: { less_than: 5.megabytes }
end
```

```erb
<%= form_with model: @user do |f| %>
  <div class="field">
    <%= f.label :avatar %>
    <%= f.file_field :avatar, 
        direct_upload: true,
        accept: "image/png,image/jpeg" %>
  </div>
  
  <% if @user.avatar.attached? %>
    <div class="preview">
      <%= image_tag @user.avatar.variant(resize_to_limit: [200, 200]) %>
    </div>
  <% end %>
  
  <%= f.submit %>
<% end %>
```

### Direct Upload Progress with Stimulus

```javascript
// app/javascript/controllers/direct_upload_controller.js
import { Controller } from "@hotwired/stimulus"
import { DirectUpload } from "@rails/activestorage"

export default class extends Controller {
  static targets = ["input", "progress", "preview"]

  upload() {
    const url = this.inputTarget.dataset.directUploadUrl
    const upload = new DirectUpload(this.inputTarget.files[0], url, this)
    
    upload.create((error, blob) => {
      if (error) {
        console.error(error)
      } else {
        this.createHiddenField(blob)
        this.showPreview(blob)
      }
    })
  }

  directUploadWillStoreFileWithXHR(request) {
    request.upload.addEventListener("progress", (event) => {
      this.progressTarget.value = event.loaded / event.total * 100
    })
  }

  createHiddenField(blob) {
    const input = document.createElement("input")
    input.type = "hidden"
    input.name = "user[avatar]"
    input.value = blob.signed_id
    this.element.appendChild(input)
  }

  showPreview(blob) {
    // Preview uploaded image
  }
}
```

### Drag and Drop Uploads

```erb
<div 
  data-controller="dropzone"
  data-dropzone-url-value="<%= rails_direct_uploads_path %>">
  
  <div data-dropzone-target="zone" class="dropzone">
    <p>Drop files here or click to upload</p>
    <%= file_field_tag :files, multiple: true, 
        data: { dropzone_target: "input" },
        direct_upload: true %>
  </div>
  
  <div data-dropzone-target="previews"></div>
</div>
```

```javascript
// app/javascript/controllers/dropzone_controller.js
import { Controller } from "@hotwired/stimulus"
import { DirectUpload } from "@rails/activestorage"

export default class extends Controller {
  static targets = ["zone", "input", "previews"]
  static values = {
    url: String
  }

  connect() {
    this.zoneTarget.addEventListener("dragover", this.highlight.bind(this))
    this.zoneTarget.addEventListener("dragleave", this.unhighlight.bind(this))
    this.zoneTarget.addEventListener("drop", this.drop.bind(this))
  }

  highlight(e) {
    e.preventDefault()
    this.zoneTarget.classList.add("highlight")
  }

  unhighlight(e) {
    e.preventDefault()
    this.zoneTarget.classList.remove("highlight")
  }

  drop(e) {
    e.preventDefault()
    this.unhighlight(e)
    
    Array.from(e.dataTransfer.files).forEach(file => this.uploadFile(file))
  }

  uploadFile(file) {
    const upload = new DirectUpload(file, this.urlValue, this)
    
    upload.create((error, blob) => {
      if (error) {
        console.error(error)
      } else {
        this.addPreview(blob, file)
        this.addHiddenField(blob)
      }
    })
  }

  addPreview(blob, file) {
    const div = document.createElement("div")
    div.className = "preview"
    div.innerHTML = `<p>${file.name}</p>`
    this.previewsTarget.appendChild(div)
  }

  addHiddenField(blob) {
    const input = document.createElement("input")
    input.type = "hidden"
    input.name = "files[]"
    input.value = blob.signed_id
    this.element.appendChild(input)
  }
}
```

## Multiple File Uploads

```ruby
# app/models/gallery.rb
class Gallery < ApplicationRecord
  has_many_attached :photos
  
  validates :photos, content_type: ['image/png', 'image/jpg', 'image/jpeg', 'image/webp'],
                     size: { less_than: 10.megabytes }
end
```

```erb
<%= form_with model: @gallery do |f| %>
  <%= f.text_field :title %>
  
  <div data-controller="multi-upload">
    <%= f.file_field :photos, 
        multiple: true, 
        direct_upload: true,
        data: { 
          multi_upload_target: "input",
          action: "change->multi-upload#upload"
        } %>
    
    <div data-multi-upload-target="progress"></div>
    <div data-multi-upload-target="previews"></div>
  </div>
  
  <%= f.submit %>
<% end %>
```

## Best Practices

### Validate Before Upload

```ruby
# app/models/concerns/attachable.rb
module Attachable
  extend ActiveSupport::Concern

  class_methods do
    def validates_attachment(name, options = {})
      validates name, content_type: options[:content_type] if options[:content_type]
      validates name, size: options[:size] if options[:size]
    end
  end
end

# app/models/user.rb
class User < ApplicationRecord
  include Attachable
  
  has_one_attached :avatar
  validates_attachment :avatar,
    content_type: ['image/png', 'image/jpg', 'image/jpeg'],
    size: { less_than: 5.megabytes }
end
```

### Handle Upload Errors

```javascript
// app/javascript/controllers/upload_controller.js
import { Controller } from "@hotwired/stimulus"

export default class extends Controller {
  static targets = ["error"]

  handleError(event) {
    const [xhr, status, error] = event.detail
    this.errorTarget.textContent = `Upload failed: ${error}`
  }
}
```

### Clean Up Orphaned Blobs

```ruby
# lib/tasks/active_storage.rake
namespace :active_storage do
  desc "Clean up orphaned blobs"
  task cleanup: :environment do
    ActiveStorage::Blob.unattached.where("created_at < ?", 2.days.ago).find_each do |blob|
      blob.purge
    end
  end
end
```

## Anti-patterns

### Not Using Direct Uploads

```ruby
# BAD: Blocks request, large files cause timeouts
def create
  @user = User.create!(user_params) # Upload happens synchronously
  redirect_to @user
end

# GOOD: Direct upload, then attach
# File uploads to storage directly from browser
# Only signed_id is sent to Rails
```

### Storing in Database

```ruby
# BAD: Base64 in database column
class User < ApplicationRecord
  # Don't do this
end

# GOOD: Use Active Storage
class User < ApplicationRecord
  has_one_attached :avatar
end
```

### Not Validating File Types

```ruby
# BAD: Accept any file
has_one_attached :document

# GOOD: Validate file type
has_one_attached :document
validates :document, content_type: { 
  in: ['application/pdf', 'application/msword'],
  message: 'must be a PDF or Word document'
}
```
