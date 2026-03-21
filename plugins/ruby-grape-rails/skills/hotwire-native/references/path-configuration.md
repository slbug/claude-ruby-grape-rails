# Path Configuration

## Path Configuration

Path configuration controls how URLs are routed in your native app:

```json
// public/native/path-configuration.json
{
  "settings": {
    "debugging": {
      "enabled": false
    }
  },
  "rules": [
    {
      "patterns": ["/sign_in", "/sign_up", "/password/*"],
      "properties": {
        "context": "modal",
        "modal_style": "form_sheet",
        "pull_to_refresh_enabled": false
      }
    },
    {
      "patterns": ["/new", "/edit"],
      "properties": {
        "context": "modal"
      }
    },
    {
      "patterns": ["/settings*"],
      "properties": {
        "presentation": "replace_root"
      }
    },
    {
      "patterns": ["/notifications"],
      "properties": {
        "context": "default",
        "title": "Notifications"
      }
    },
    {
      "patterns": ["/native/*"],
      "properties": {
        "presentation": "native"
      }
    },
    {
      "patterns": ["*"],
      "properties": {
        "context": "default",
        "pull_to_refresh_enabled": true
      }
    }
  ]
}
```

### Path Configuration Rules

| Property | Values | Description |
|----------|--------|-------------|
| `context` | `default`, `modal` | Presentation style |
| `presentation` | `default`, `replace_root`, `native` | Navigation behavior |
| `modal_style` | `form_sheet`, `page_sheet`, `full_screen` | iOS modal style |
| `pull_to_refresh_enabled` | `true`, `false` | Enable pull-to-refresh |
| `title` | string | Override navigation title |

### Loading Path Configuration

```ruby
# config/routes.rb
Rails.application.routes.draw do
  # Serve path configuration
  get '/native/path-configuration', to: 'native#path_configuration'
end
```

```ruby
# app/controllers/native_controller.rb
class NativeController < ApplicationController
  def path_configuration
    render json: {
      settings: {
        debugging: { enabled: Rails.env.development? }
      },
      rules: path_rules
    }
  end
  
  private
  
  def path_rules
    [
      {
        patterns: ["/sign_in", "/sign_up"],
        properties: { context: "modal" }
      },
      {
        patterns: ["*"],
        properties: { 
          context: "default",
          pull_to_refresh_enabled: true 
        }
      }
    ]
  end
end
```
