## Rails 8 Authentication Generator

Built-in authentication replaces Devise for new apps:

Generate the authentication scaffold: `bin/rails generate authentication`.

This creates:

- `Session` model for token storage
- `Current` model for request-scoped state
- `PasswordsController` for resets
- `SessionsController` for login/logout

```ruby
# app/controllers/concerns/authentication.rb
class ApplicationController < ActionController::Base
  include Authentication  # Generated concern
end

# Usage in controllers
before_action :require_authentication

# Access current user
current_user  # From Current.session.user
```

### Migration from Devise

When staying with Devise:

```ruby
# Keep Devise for complex needs:
# - OAuth providers
# - Confirmable
# - Lockable
# - Trackable

# Use built-in auth for:
# - Simple email/password
# - Password resets
# - Session management
# - Token authentication
```
