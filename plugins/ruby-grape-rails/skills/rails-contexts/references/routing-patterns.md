# Routing Patterns Reference

## Named Routes (path helpers) - Rails

```ruby
# ALWAYS use named routes or url helpers
post_path(@post)
search_path(q: user_input)  # Auto URL-encoded

# In views
link_to "Post", post_path(@post)
# Or shorthand
link_to "Post", @post
```

## Routes Configuration

```ruby
Rails.application.routes.draw do
  # Browser routes with authentication
  authenticate :user do
    get 'dashboard', to: 'dashboard#index'
  end
  
  # API routes
  namespace :api do
    namespace :v1 do
      resources :users, only: [:index, :show]
    end
  end
  
  # Resourceful routes
  resources :posts do
    resources :comments, shallow: true
  end
end
```

## Anti-patterns (DON'T DO THESE)

### Fat Controllers (Not Rails)

```ruby
# WRONG: Business logic in controller
class UsersController < ApplicationController
  def create
    # 20 lines of validation and business logic...
    if params[:user][:email].present? && params[:user][:password].length >= 8
      user = User.new(params[:user])
      if user.save
        UserMailer.welcome(user).deliver_later
        redirect_to user_path(user)
      else
        render :new
      end
    end
  end
end

# RIGHT: Delegate to service/context
class UsersController < ApplicationController
  def create
    result = UserRegistration.call(params[:user])
    
    if result.success?
      redirect_to user_path(result.user)
    else
      @errors = result.errors
      render :new, status: :unprocessable_entity
    end
  end
end
```

### Direct Model Access in Controllers (Don't)

Model is already the repository. Don't wrap it unnecessarily.

### God Service (Don't)

Split when > 400 lines or when domains are distinct.

### Model Callbacks with Side Effects (Don't)

Use service objects for side effects instead of callbacks.

### Reaching Across Domains (Don't)

```ruby
# WRONG
class OrderService
  def create_order(user_id, params)
    user = User.find(user_id)  # Bypassing Accounts domain!
    # ...
  end
end

# RIGHT
class OrderService
  def create_order(user_id, params)
    user = Accounts.get_user(user_id)
    return Result.error(:user_not_found) unless user
    # ...
  end
end
```

### Direct DB Queries in Controllers (Don't)

```ruby
# WRONG: Complex queries in controller
class UsersController < ApplicationController
  def index
    @users = User.includes(:posts, :comments).where(active: true)
                   .order(:created_at).page(params[:page])
  end
end

# RIGHT: Delegate to query object or scope
class UsersController < ApplicationController
  def index
    @users = User.active.recent.page(params[:page])
  end
end
```
