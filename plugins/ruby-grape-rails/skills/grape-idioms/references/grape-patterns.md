# Grape API Patterns Reference

## Parameter Declaration and Coercion

### Basic Params Block

```ruby
class UsersAPI < Grape::API
  resource :users do
    desc "Create a user"
    params do
      requires :name, type: String, desc: "User's full name"
      requires :email, type: String, regexp: URI::MailTo::EMAIL_REGEXP
      optional :age, type: Integer, values: 0..120
      optional :role, type: String, default: "user", values: %w[user admin moderator]
    end
    post do
      User.create!(declared(params, include_missing: false))
    end
  end
end
```

### Nested Parameters

```ruby
params do
  requires :user, type: Hash do
    requires :name, type: String
    requires :email, type: String
    optional :profile, type: Hash do
      optional :bio, type: String
      optional :location, type: String
    end
  end
  optional :preferences, type: Hash do
    optional :newsletter, type: Boolean, default: false
    optional :theme, type: String, values: %w[light dark], default: "light"
  end
end
```

### Array Parameters

```ruby
params do
  optional :tags, type: Array[String]
  optional :scores, type: Array[Integer]
  optional :addresses, type: Array[Hash] do
    requires :street, type: String
    requires :city, type: String
    requires :zip, type: String
  end
end
```

## declared() Semantics

The `declared()` helper filters params to only those defined in the params block:

```ruby
# Request: POST /users?name=John&email=john@example.com&admin=true&foo=bar

# Without declared() - dangerous
User.create(params)  # Creates user with admin=true!

# With declared(params) - safe but includes defaults
params
# => { "name" => "John", "email" => "john@example.com", "role" => "user", "preferences" => { "newsletter" => false, "theme" => "light" } }

# With declared(params, include_missing: false) - clean
params
# => { "name" => "John", "email" => "john@example.com" }
```

### Common declared() Patterns

```ruby
# Basic - include all declared params with defaults
declared(params)

# Exclude missing optional params - preferred for updates
declared(params, include_missing: false)

# Include parents - for nested structures
declared(params, include_parent_names: true)

# Combined - most common pattern for updates
declared(params, include_missing: false, include_parent_names: false)
```

## Conditional Params with evaluate_given

Use `evaluate_given` to conditionally require params based on other values:

```ruby
params do
  requires :type, type: String, values: %w[personal business]
  
  given type: ->(val) { val == "personal" } do
    requires :first_name, type: String
    requires :last_name, type: String
  end
  
  given type: ->(val) { val == "business" } do
    requires :company_name, type: String
    requires :tax_id, type: String
  end
end
```

### Multiple Conditions

```ruby
params do
  requires :action, type: String, values: %w[create update delete]
  requires :resource_type, type: String, values: %w[post comment user]
  
  given action: "create", resource_type: "post" do
    requires :title, type: String
    requires :content, type: String
  end
  
  given action: "update" do
    requires :id, type: Integer
    at_least_one_of :title, :content, :published
  end
end
```

## Custom Parameter Builders with build_with

Override how Grape builds params:

```ruby
class JsonParamsBuilder < Grape::Validations::ParamsScopeBuilder
  def call(env)
    # Custom param building logic
    request = Rack::Request.new(env)
    
    if request.content_type == "application/json"
      JSON.parse(request.body.read)
    else
      super
    end
  end
end

class MyAPI < Grape::API
  build_with JsonParamsBuilder
  
  # ... endpoints
end
```

## Error Handling and Envelopes

### Consistent Error Format

```ruby
class BaseAPI < Grape::API
  format :json
  
  # Validation errors
  rescue_from Grape::Exceptions::ValidationErrors do |e|
    error!({
      error: "validation_error",
      message: "One or more parameters are invalid",
      details: e.errors.transform_values { |v| v.map(&:to_s) }
    }, 422)
  end
  
  # Record not found
  rescue_from ActiveRecord::RecordNotFound do |e|
    error!({
      error: "not_found",
      message: "Resource not found"
    }, 404)
  end
  
  # Authorization
  rescue_from CanCan::AccessDenied do |e|
    error!({
      error: "forbidden",
      message: "You don't have permission to perform this action"
    }, 403)
  end
  
  # Generic fallback
  rescue_from :all do |e|
    if Rails.env.production?
      error!({
        error: "internal_error",
        message: "An unexpected error occurred"
      }, 500)
    else
      raise e
    end
  end
end
```

### Error Response Structure

```json
{
  "error": "validation_error",
  "message": "One or more parameters are invalid",
  "details": {
    "email": ["is not a valid email address"],
    "age": ["must be less than or equal to 120"]
  }
}
```

## Versioning Strategies

### Path Versioning (Recommended)

```ruby
class API < Grape::API
  prefix :api
  
  version "v1", using: :path do
    mount V1::UsersAPI
    mount V1::PostsAPI
  end
  
  version "v2", using: :path do
    mount V2::UsersAPI
    mount V2::PostsAPI
  end
end

# Routes:
# /api/v1/users
# /api/v2/users
```

### Header Versioning

```ruby
class API < Grape::API
  version "v1", using: :header, vendor: "myapp" do
    # Accessible via: Accept: application/vnd.myapp-v1+json
  end
end
```

### Parameter Versioning

```ruby
class API < Grape::API
  version "v1", using: :param, parameter: "api_version" do
    # Accessible via: ?api_version=v1
  end
end
```

### Versioning Trade-offs

| Strategy | Pros | Cons |
|----------|------|------|
| Path | Cache-friendly, explicit, bookmarkable | URL changes between versions |
| Header | Clean URLs | Harder to test, not cache-friendly |
| Param | Flexible | Pollutes query string |

## Mounted API Boundaries

### Organizing Large APIs

```ruby
# config/routes.rb
Rails.application.routes.draw do
  mount API::Base => "/api"
end

# app/api/api/base.rb
module API
  class Base < Grape::API
    prefix :api
    format :json
    
    # Global middleware
    use Rack::ETag
    
    # Auth
    before do
      authenticate! unless request.path == "/api/health"
    end
    
    mount API::V1::Base => "/v1"
    mount API::V2::Base => "/v2"
    
    # Health check (outside versioning)
    get :health do
      { status: "ok", timestamp: Time.current }
    end
  end
end

# app/api/api/v1/base.rb
module API
  module V1
    class Base < Grape::API
      version "v1", using: :path
      
      mount UsersAPI
      mount PostsAPI
      mount CommentsAPI
    end
  end
end
```

### Namespacing and Mounting

```ruby
module API
  module V1
    class UsersAPI < Grape::API
      resource :users do
        desc "Get all users"
        get do
          User.all
        end
        
        route_param :id do
          desc "Get a user"
          get do
            User.find(params[:id])
          end
          
          desc "Update a user"
          params do
            optional :name, type: String
            optional :email, type: String
            at_least_one_of :name, :email
          end
          put do
            user = User.find(params[:id])
            user.update!(declared(params, include_missing: false))
            user
          end
        end
      end
    end
  end
end
```

## Entity/Presenter Patterns

### Basic Entity

```ruby
module API
  module Entities
    class User < Grape::Entity
      expose :id
      expose :name
      expose :email
      expose :created_at, as: :joined_at
      
      expose :profile, using: API::Entities::Profile, if: ->(user, opts) { user.profile.present? }
      
      expose :post_count do |user|
        user.posts.count
      end
    end
  end
end

# Usage
present User.all, with: API::Entities::User
```

### Conditional Exposure

```ruby
class User < Grape::Entity
  expose :id
  expose :name
  expose :email, if: ->(user, opts) { opts[:current_user]&.admin? || user.public_profile? }
  expose :admin, if: ->(user, opts) { opts[:current_user]&.admin? }
  
  expose :private_notes, if: ->(user, opts) { opts[:current_user]&.can_view_notes?(user) }
end
```

## Authentication Patterns

### Token-Based Auth

```ruby
class BaseAPI < Grape::API
  helpers do
    def authenticate!
      token = headers["Authorization"]&.gsub("Bearer ", "")
      error!("Unauthorized", 401) unless token
      
      @current_user = User.find_by(api_token: token)
      error!("Unauthorized", 401) unless @current_user
    end
    
    def current_user
      @current_user
    end
  end
  
  before do
    authenticate!
  end
end
```

### OAuth/JWT

```ruby
helpers do
  def authenticate!
    token = headers["Authorization"]&.gsub("Bearer ", "")
    error!("Unauthorized", 401) unless token
    
    begin
      payload = JWT.decode(token, Rails.application.credentials.secret_key_base)[0]
      @current_user = User.find(payload["user_id"])
    rescue JWT::DecodeError
      error!("Invalid token", 401)
    end
  end
end
```

## Testing Grape APIs

### Request Specs

```ruby
require "rails_helper"

RSpec.describe "Users API", type: :request do
  describe "POST /api/v1/users" do
    context "with valid params" do
      let(:valid_params) do
        {
          user: {
            name: "John Doe",
            email: "john@example.com"
          }
        }
      end
      
      it "creates a user" do
        post "/api/v1/users", params: valid_params
        
        expect(response).to have_http_status(:created)
        expect(JSON.parse(response.body)["name"]).to eq("John Doe")
      end
    end
    
    context "with invalid params" do
      let(:invalid_params) do
        { user: { name: "" } }
      end
      
      it "returns validation errors" do
        post "/api/v1/users", params: invalid_params
        
        expect(response).to have_http_status(:unprocessable_entity)
        expect(JSON.parse(response.body)["error"]).to eq("validation_error")
      end
    end
  end
end
```

## Rails Integration

### Mounting in Routes

```ruby
Rails.application.routes.draw do
  mount API::Base => "/api"
  
  # Regular Rails routes
  resources :posts
  
  # Catch-all for SPA (after API mount)
  get "*path", to: "home#index", constraints: ->(req) {
    !req.xhr? && req.format.html?
  }
end
```

### Sharing Logic with Rails

```ruby
# app/services/user_creator.rb - shared service
class UserCreator
  def self.call(attrs)
    User.create!(attrs)
  end
end

# Used in both Rails controllers and Grape APIs
class UsersController < ApplicationController
  def create
    @user = UserCreator.call(user_params)
    redirect_to @user
  end
end

class API::V1::UsersAPI < Grape::API
  post do
    UserCreator.call(declared(params, include_missing: false))
  end
end
```
