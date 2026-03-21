# Best Practices

## Best Practices

1. **Feature Detection**: Check if running in native app before using bridge

```javascript
// app/javascript/helpers/native.js
export function isNativeApp() {
  return navigator.userAgent.includes('HotwireNative') ||
         window.bridge !== undefined
}

// Usage
if (isNativeApp()) {
  // Use native date picker
} else {
  // Use HTML5 date input
}
```

2. **Graceful Degradation**: Always provide web fallback

```erb
<% if native_app? %>
  <div data-controller="bridge--datepicker">
    <%= f.text_field :date, data: { bridge__datepicker_target: 'input' } %>
    <button data-action="click->bridge--datepicker#open">Select Date</button>
  </div>
<% else %>
  <%= f.date_field :date %>
<% end %>
```

3. **Version Bridge Components**: Keep web and native in sync

```json
// public/native/version.json
{
  "bridgeComponents": {
    "datepicker": "1.2.0",
    "camera": "1.0.0",
    "location": "2.1.0"
  }
}
```

4. **Handle Bridge Unavailability**: Components should work without bridge

```javascript
connect() {
  super.connect()
  
  if (this.bridgeConnected) {
    this.send('connect')
  } else {
    // Fallback to web implementation
    this.setupWebDatepicker()
  }
}
```

5. **Optimize for Mobile**: Native apps expect snappy performance

```ruby
# app/controllers/concerns/native_optimization.rb
module NativeOptimization
  extend ActiveSupport::Concern
  
  included do
    before_action :optimize_for_native, if: :native_app_request?
  end
  
  private
  
  def native_app_request?
    request.user_agent&.include?('HotwireNative')
  end
  
  def optimize_for_native
    # Skip layout elements native app doesn't need
    @skip_header = true
    @skip_footer = true
    
    # Use native navigation titles
    @use_native_title = true
  end
end
```
