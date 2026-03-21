# Strong Parameters and params.expect Reference

## Iron Law: Never Trust User Input

Always whitelist parameters. Never use `params` directly in model methods.

## Traditional strong_parameters Pattern

```ruby
class UsersController < ApplicationController
  def create
    @user = User.new(user_params)  # Safe - whitelisted
    # DON'T: User.new(params[:user])  # DANGEROUS - mass assignment vulnerability
  end

  private

  def user_params
    params.require(:user).permit(:name, :email, :password)
  end
end
```

## Modern `params.expect` Pattern (Rails 8+)

Rails 8 introduces `params.expect` as a cleaner alternative to `require().permit()`:

```ruby
class UsersController < ApplicationController
  def create
    @user = User.new(user_params)
  end

  def update
    @user.update(user_params)
  end

  private

  # PREFER: params.expect for new Rails 8+ apps
  def user_params
    params.expect(user: [:name, :email, :password])
  end
end
```

### `params.expect` Syntax

```ruby
# Simple attributes
params.expect(:name, :email, :age)

# Nested objects
params.expect(user: [:name, :email, :password])

# Deep nesting
params.expect(order: [
  :customer_name,
  :customer_email,
  { items: [:product_id, :quantity, :price] },
  { shipping_address: [:street, :city, :zip] }
])

# Arrays
params.expect(tags: [])                    # Array of scalars
params.expect(user: { roles: [] })         # Array within nested hash

# Mixed types
params.expect(product: [
  :name,
  :description,
  :price,
  { categories: [] },
  { variants: [:size, :color, :sku] }
])
```

### Comparison: `require.permit` vs `expect`

| Aspect | `require(:key).permit(...)` | `params.expect(...)` |
|--------|---------------------------|----------------------|
| Missing key | Raises `ActionController::ParameterMissing` | Raises `ActionController::ParameterMissing` |
| Extra params | Silently filtered | Silently filtered |
| Syntax | Method chain | Hash-like DSL |
| Rails version | All | 8.0+ |
| Readability | Verbose | Declarative |

## Complex Parameter Patterns

### Nested Forms

```ruby
# Form with nested address
class UsersController < ApplicationController
  def user_params
    params.expect(user: [
      :name,
      :email,
      { profile_attributes: [:bio, :location, :website] }
    ])
  end
end
```

### Polymorphic Associations

```ruby
class CommentsController < ApplicationController
  def comment_params
    params.expect(comment: [:body, :commentable_type, :commentable_id])
  end
end
```

### File Uploads

```ruby
class DocumentsController < ApplicationController
  def document_params
    params.expect(document: [:title, :description, :file])
  end
end
```

## Array Parameters

```ruby
# Single array of values
params.expect(tags: [])
# Input: { tags: ["ruby", "rails", "hotwire"] }
# Output: { "tags" => ["ruby", "rails", "hotwire"] }

# Array of objects
params.expect(users: [[:name, :email]])
# Input: { users: [{ name: "A", email: "a@example.com" }, ...] }

# Within nested object
params.expect(project: [
  :name,
  { member_ids: [] }
])
```

## Conditional Permitting

```ruby
class UsersController < ApplicationController
  def user_params
    base = [:name, :email]
    base << :admin if current_user.admin?
    
    params.expect(user: base)
  end
end
```

## Strong Parameters with POROs

When not using Active Record models directly:

```ruby
class ApiController < ApplicationController
  def search_params
    params.expect(search: [:query, :sort, :order])
      .to_h
      .symbolize_keys
  end
end

# Usage in service
result = SearchService.call(**search_params)
```

## Security Considerations

```ruby
# NEVER permit all
params.permit!  # DANGEROUS - allows any parameter

# NEVER use user-controlled keys
params[:model_type].constantize  # DANGEROUS - RCE risk

# ALWAYS whitelist explicitly
allowed_models = %w[User Post Comment]
model = allowed_models.find { |m| m == params[:type] }
model&.constantize
```

## Migration from `require.permit` to `expect`

```ruby
# Before (Rails 7.x and earlier)
def user_params
  params.require(:user).permit(:name, :email, :password)
end

# After (Rails 8+)
def user_params
  params.expect(user: [:name, :email, :password])
end
```

## Testing Parameter Permitting

```ruby
require "test_helper"

class UsersControllerTest < ActionDispatch::IntegrationTest
  test "should filter unpermitted params" do
    post users_url, params: {
      user: {
        name: "John",
        email: "john@example.com",
        admin: true,  # Should be filtered
        password: "secret"
      }
    }
    
    user = User.last
    assert_equal "John", user.name
    assert_not user.admin?  # Filtered out
  end
end
```

## Common Patterns

### API Controllers

```ruby
class Api::V1::BaseController < ApplicationController
  private

  def pagination_params
    params.expect(page: [:number, :size])
      .to_h
      .deep_symbolize_keys
  end

  def filter_params
    params.expect(filter: [])
  end
end
```

### Grape API

```ruby
class UsersAPI < Grape::API
  params do
    optional :page, type: Integer, default: 1
    optional :per_page, type: Integer, default: 20
    optional :filter, type: Hash do
      optional :status, type: String
      optional :role, type: String
    end
  end
  get "/users" do
    # params already validated and coerced by Grape
    User.filter(declared(params, include_missing: false))
  end
end
```
