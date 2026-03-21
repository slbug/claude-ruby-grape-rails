# Authorization Patterns Reference

## Pundit (Recommended)

```ruby
# Gemfile
gem 'pundit'

# app/controllers/application_controller.rb
class ApplicationController < ActionController::Base
  include Pundit::Authorization
  
  rescue_from Pundit::NotAuthorizedError, with: :user_not_authorized
  
  private
  
  def user_not_authorized
    flash[:alert] = "You are not authorized to perform this action."
    redirect_to(request.referrer || root_path)
  end
end

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
    record.published? || record.user_id == user.id || user.admin?
  end
  
  def update?
    record.user_id == user.id || user.admin?
  end
  
  def destroy?
    record.user_id == user.id || user.admin?
  end
  
  class Scope < Scope
    def resolve
      if user.admin?
        scope.all
      else
        scope.where(published: true).or(scope.where(user_id: user.id))
      end
    end
  end
end

# app/controllers/posts_controller.rb
class PostsController < ApplicationController
  def show
    post = Post.find(params[:id])
    authorize post
    @post = post
  end
  
  def index
    @posts = policy_scope(Post)
  end
  
  def update
    post = Post.find(params[:id])
    authorize post
    
    if post.update(post_params)
      redirect_to post
    else
      render :edit
    end
  end
end
```

## CanCanCan

```ruby
# Gemfile
gem 'cancancan'

# app/models/ability.rb
class Ability
  include CanCan::Ability

  def initialize(user)
    user ||= User.new # guest user (not logged in)

    if user.admin?
      can :manage, :all
    else
      can :read, Post, published: true
      can :manage, Post, user_id: user.id
      can :read, Comment
      can :create, Comment
      can :destroy, Comment, user_id: user.id
    end
  end
end

# app/controllers/posts_controller.rb
class PostsController < ApplicationController
  load_and_authorize_resource
  
  def show
    # @post already loaded and authorized
  end
  
  def update
    if @post.update(post_params)
      redirect_to @post
    else
      render :edit
    end
  end
end
```

## Manual Authorization

```ruby
class PostsController < ApplicationController
  before_action :set_post, only: [:show, :edit, :update, :destroy]
  before_action :authorize_post, only: [:edit, :update, :destroy]
  
  def show
    # Anyone can view published posts
    raise ActiveRecord::RecordNotFound unless @post.published? || @post.user_id == current_user.id
  end
  
  def update
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
  
  def authorize_post
    unless @post.user_id == current_user.id || current_user.admin?
      redirect_to root_path, alert: 'Not authorized'
    end
  end
end
```

## Authorization in Service Objects

```ruby
class PostService
  def initialize(user)
    @user = user
  end
  
  def update(post_id, attributes)
    post = Post.find(post_id)
    
    # Authorization
    unless can_update?(post)
      raise NotAuthorizedError, "Cannot update this post"
    end
    
    post.update!(attributes)
    post
  end
  
  def destroy(post_id)
    post = Post.find(post_id)
    
    unless can_destroy?(post)
      raise NotAuthorizedError, "Cannot delete this post"
    end
    
    post.destroy!
  end
  
  private
  
  attr_reader :user
  
  def can_update?(post)
    post.user_id == user.id || user.admin?
  end
  
  def can_destroy?(post)
    post.user_id == user.id || user.admin?
  end
end

class NotAuthorizedError < StandardError; end
```

## Scoping in Queries

```ruby
class User < ApplicationRecord
  has_many :posts
  has_many :visible_posts, -> { visible_to(self) }, class_name: 'Post'
end

class Post < ApplicationRecord
  belongs_to :user
  
  scope :published, -> { where(published: true) }
  scope :owned_by, ->(user) { where(user_id: user.id) }
  scope :visible_to, ->(user) {
    if user.admin?
      all
    else
      published.or(owned_by(user))
    end
  }
end

# Usage
@posts = Post.visible_to(current_user).order(:created_at)
```

## API Authorization

```ruby
class Api::PostsController < Api::BaseController
  def index
    @posts = Post.visible_to(current_user)
    render json: @posts
  end
  
  def show
    @post = Post.find(params[:id])
    
    unless @post.visible_to?(current_user)
      render json: { error: 'Not found' }, status: :not_found
      return
    end
    
    render json: @post
  end
  
  def update
    @post = Post.find(params[:id])
    
    unless @post.user_id == current_user.id
      render json: { error: 'Unauthorized' }, status: :unauthorized
      return
    end
    
    if @post.update(post_params)
      render json: @post
    else
      render json: { errors: @post.errors }, status: :unprocessable_entity
    end
  end
end
```

## Testing Authorization

```ruby
RSpec.describe PostPolicy do
  subject { described_class }
  
  let(:user) { create(:user) }
  let(:admin) { create(:user, :admin) }
  let(:other_user) { create(:user) }
  let(:post) { create(:post, user: user) }
  
  permissions :update?, :destroy? do
    it "allows owner" do
      expect(subject).to permit(user, post)
    end
    
    it "allows admin" do
      expect(subject).to permit(admin, post)
    end
    
    it "denies other users" do
      expect(subject).not_to permit(other_user, post)
    end
  end
end
```
