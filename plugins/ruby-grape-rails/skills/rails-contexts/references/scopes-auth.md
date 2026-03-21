# Scopes and Authorization Reference

## Contents

- [Pundit/CanCanCan Integration](#punditcancancan-integration)
- [Manual Authorization Pattern](#manual-authorization-pattern)
- [Controller Filters](#controller-filters)
- [API Authentication](#api-authentication)

## Pundit/CanCanCan Integration

For Rails projects, use established authorization gems.

### Pundit Setup

```ruby
# app/policies/application_policy.rb
class ApplicationPolicy
  attr_reader :user, :record

  def initialize(user, record)
    @user = user
    @record = record
  end

  def index?
    false
  end

  def show?
    false
  end

  def create?
    false
  end

  def new?
    create?
  end

  def update?
    false
  end

  def edit?
    update?
  end

  def destroy?
    false
  end

  class Scope
    def initialize(user, scope)
      @user = user
      @scope = scope
    end

    def resolve
      scope.none
    end

    private

    attr_reader :user, :scope
  end
end

# app/policies/post_policy.rb
class PostPolicy < ApplicationPolicy
  def show?
    user.present?
  end

  def update?
    user.present? && record.user_id == user.id
  end

  def destroy?
    update?
  end

  class Scope < Scope
    def resolve
      if user.admin?
        scope.all
      else
        scope.where(user_id: user.id)
      end
    end
  end
end
```

### Pundit Configuration

Add to ApplicationController:

```ruby
class ApplicationController < ActionController::Base
  include Pundit::Authorization

  rescue_from Pundit::NotAuthorizedError, with: :user_not_authorized

  private

  def user_not_authorized
    flash[:alert] = "You are not authorized to perform this action."
    redirect_to(request.referrer || root_path)
  end
end
```

### Using Pundit in Controllers

```ruby
class PostsController < ApplicationController
  before_action :set_post, only: [:show, :edit, :update, :destroy]

  def index
    @posts = policy_scope(Post)
  end

  def show
    authorize @post
  end

  def update
    authorize @post
    if @post.update(post_params)
      redirect_to @post
    else
      render :edit
    end
  end

  private

  def set_post
    @post = Post.find(params[:id])
  end
end
```

### Multi-Tenant Scope Pattern

Extend scope for organizations:

```ruby
class OrganizationScope
  attr_reader :user, :organization

  def initialize(user, organization = nil)
    @user = user
    @organization = organization
  end

  def self.for_user(user)
    new(user)
  end

  def with_organization(org)
    OrganizationScope.new(user, org)
  end
end
```

Controller concern for augmentation:

```ruby
module OrganizationScoped
  extend ActiveSupport::Concern

  included do
    before_action :set_organization_scope
  end

  private

  def set_organization_scope
    if params[:org_id]
      org = Organization.find(params[:org_id])
      @current_scope = current_scope.with_organization(org)
    end
  end
end
```

## Manual Authorization Pattern

For simple cases without Pundit.

### Authority Pattern

```ruby
# app/models/authority.rb
class Authority
  attr_reader :user, :tenant_id, :permissions

  def initialize(user, opts = {})
    @user = user
    @tenant_id = opts[:tenant_id] || (user && user.tenant_id)
    @permissions = opts[:permissions] || []
  end

  def self.guest
    new(nil)
  end

  def guest?
    user.nil?
  end

  def can?(action, resource)
    return false if guest?
    # Custom permission logic
    permissions.include?(action)
  end
end
```

### Using Authority in Services

```ruby
class PostService
  def initialize(authority)
    @authority = authority
  end

  def list_posts
    if @authority.guest?
      Post.published
    else
      Post.where(tenant_id: @authority.tenant_id)
    end
  end

  def create_post(attrs)
    return Result.error(:unauthorized) if @authority.guest?
    
    Post.create!(
      attrs.merge(author_id: @authority.user.id, tenant_id: @authority.tenant_id)
    )
  end
end
```

### Controller for Building Authority

```ruby
class ApplicationController < ActionController::Base
  before_action :build_authority

  private

  def build_authority
    @authority = if current_user
      Authority.new(current_user)
    else
      Authority.guest
    end
  end
end
```

## Controller Filters

### Authentication Filter

```ruby
class ApplicationController < ActionController::Base
  before_action :authenticate_user!, except: [:home, :about]

  private

  def authenticate_user!
    unless user_signed_in?
      flash[:error] = "You must log in to access this page."
      redirect_to new_user_session_path
    end
  end
end
```

### Authorization Filter (action-specific)

```ruby
class PostsController < ApplicationController
  before_action :authorize_resource, only: [:edit, :update, :destroy]

  private

  def authorize_resource
    unless @post.user_id == current_user.id
      flash[:error] = "Unauthorized"
      redirect_to root_path
    end
  end
end
```

### Fetch Resource Filter

```ruby
class MessagesController < ApplicationController
  before_action :set_message, only: [:show, :edit, :update, :destroy]

  private

  def set_message
    @message = Message.find(params[:id])
  end
end
```

## API Authentication

### Token-based Authentication

```ruby
class Api::BaseController < ActionController::API
  before_action :authenticate_api_user!

  private

  def authenticate_api_user!
    token = request.headers['Authorization']&.split(' ')&.last
    
    if token
      @current_user = User.find_by(api_token: token)
    end

    unless @current_user
      render json: { error: 'Invalid or missing token' }, status: :unauthorized
    end
  end
end
```

### JWT Authentication

```ruby
class Api::BaseController < ActionController::API
  before_action :authenticate_user_from_token!

  private

  def authenticate_user_from_token!
    token = request.headers['Authorization']&.split(' ')&.last
    
    begin
      payload = JWT.decode(token, Rails.application.credentials.secret_key_base)[0]
      @current_user = User.find(payload['user_id'])
    rescue JWT::ExpiredSignature, JWT::VerificationError, JWT::DecodeError
      render json: { error: 'Invalid token' }, status: :unauthorized
    end
  end
end
```
