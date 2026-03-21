# Middleware/Before-Action Patterns Reference

Rails uses `before_action` (or `before_action`) in controllers and Rack middleware for request handling.

## Before-Action Filters

Accept `request` context, modify or halt request flow. Defined in the controller:

```ruby
before_action :authenticate_user!

private

def authenticate_user!
  unless current_user
    flash[:error] = "Must log in"
    redirect_to login_path
  end
end
```

**CRITICAL**: Always `return` after `redirect_to` or `render` in before-actions.
Without explicit return, controller action still executes.

## Rack Middleware

Implement `initialize(app)` and `call(env)`:

```ruby
class LocaleMiddleware
  def initialize(app)
    @app = app
    @default_locale = 'en'
  end

  def call(env)
    request = ActionDispatch::Request.new(env)
    locale = request.params['locale'] || @default_locale
    env['locale'] = locale
    @app.call(env)
  end
end

# Usage in config/application.rb
config.middleware.use LocaleMiddleware
```

**Optimization**: `initialize` runs at boot time. Put expensive setup there, not in `call`.

## Middleware Placement

| Location | Scope | Example |
|----------|-------|---------|
| config.middleware | Every request | Static files, session, parsers |
| ApplicationController | All controllers | Auth, API token validation |
| Specific controller | Action-specific | Resource loading, authorization |

### Controller-Level Before-Action Guards

```ruby
class PostsController < ApplicationController
  # Only for specific actions
  before_action :fetch_post, only: [:show, :edit, :update, :destroy]
  before_action :authorize_post, only: [:edit, :update, :destroy]

  private

  def fetch_post
    @post = Post.find(params[:id])
  end

  def authorize_post
    unless @post.user_id == current_user.id
      flash[:error] = "Unauthorized"
      redirect_to root_path
    end
  end
end
```

## Middleware Stack Order

Default Rails middleware stack:

```ruby
# 1. Static assets (before anything else)
config.middleware.insert_before ActionDispatch::Static, 
  ActionDispatch::Static, app, paths["public"].first

# 2. Request metadata
config.middleware.use ActionDispatch::RequestId
config.middleware.use Rails::Rack::Logger

# 3. Body parsing
config.middleware.use ActionDispatch::ParamsParser

# 4. Session
config.middleware.use ActionDispatch::Session::CookieStore

# 5. Router (last)
config.middleware.use ActionDispatch::Routing::RouteSet
```

## Common Middleware Patterns

### Rate Limiting Middleware

```ruby
class RateLimitMiddleware
  def initialize(app)
    @app = app
  end

  def call(env)
    request = ActionDispatch::Request.new(env)
    key = rate_limit_key(request)
    
    if RateLimit.check(key, limit: 60, window: 60)
      @app.call(env)
    else
      [429, { 'retry-after' => '60' }, ['Too Many Requests']]
    end
  end

  private

  def rate_limit_key(request)
    request.remote_ip.to_s
  end
end
```

### CORS Middleware

```ruby
# Use rack-cors with explicit origins (never wildcard in prod)
config.middleware.insert_before ActionDispatch::Static, Rack::Cors do
  allow do
    origins 'https://app.example.com', 'https://admin.example.com'
    resource '*', headers: :any, methods: [:get, :post, :put, :patch, :delete]
  end
end
```

## Anti-patterns

| Wrong | Right |
|-------|-------|
| No `return` after redirect/render | Always `return` after redirect/render |
| Expensive work in `call` DB calls | `call` for request handling only, DB queries cached |
| Auth in middleware for all requests | Auth in ApplicationController |
| All logic in middleware | Split by controller concern |
