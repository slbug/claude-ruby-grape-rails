# JSON and API Patterns Reference

## JSON Controller Pattern

```ruby
# app/controllers/api/posts_controller.rb
module Api
  class PostsController < ApplicationController
    before_action :set_post, only: [:show, :update, :destroy]
    before_action :authenticate_user!
    
    rescue_from ActiveRecord::RecordNotFound, with: :not_found
    rescue_from ActiveRecord::RecordInvalid, with: :unprocessable

    def index
      @posts = current_user.posts.includes(:author, :comments)
      render json: @posts
    end

    def create
      @post = current_user.posts.build(post_params)
      
      if @post.save
        render json: @post, status: :created, location: api_post_url(@post)
      else
        render json: { errors: @post.errors }, status: :unprocessable_entity
      end
    end

    def show
      render json: @post
    end

    def update
      if @post.update(post_params)
        render json: @post
      else
        render json: { errors: @post.errors }, status: :unprocessable_entity
      end
    end

    def destroy
      @post.destroy
      head :no_content
    end

    private

    def set_post
      @post = current_user.posts.find(params[:id])
    end

    def post_params
      params.require(:post).permit(:title, :body, :published)
    end

    def not_found
      render json: { error: "Not found" }, status: :not_found
    end

    def unprocessable(exception)
      render json: { error: exception.message }, status: :unprocessable_entity
    end
  end
end
```

## Serializer Pattern (with ActiveModel::Serializers)

```ruby
# app/serializers/post_serializer.rb
class PostSerializer < ActiveModel::Serializer
  attributes :id, :title, :body, :published, :created_at, :updated_at
  
  belongs_to :author, serializer: UserSerializer
  has_many :comments
  
  attribute :reading_time do
    object.body.split(' ').length / 200  # ~200 words per minute
  end
  
  def created_at
    object.created_at.iso8601
  end
end

# app/serializers/user_serializer.rb
class UserSerializer < ActiveModel::Serializer
  attributes :id, :name, :email, :avatar_url
  
  def avatar_url
    object.avatar.attached? ? Rails.application.routes.url_helpers.url_for(object.avatar) : nil
  end
end

# Usage in controller
def show
  @post = Post.find(params[:id])
  render json: @post, serializer: PostSerializer, include: ['author', 'comments']
end
```

## JSON:API Specification Pattern

```ruby
# app/controllers/concerns/json_api_concern.rb
module JsonApiConcern
  extend ActiveSupport::Concern

  included do
    before_action :validate_content_type, only: [:create, :update]
  end

  private

  def validate_content_type
    unless request.content_type == 'application/vnd.api+json'
      render json: { error: 'Unsupported Media Type' }, status: :unsupported_media_type
    end
  end

  def render_jsonapi(resource, options = {})
    render json: JsonApiSerializer.new(resource, options).serializable_hash.to_json,
           content_type: 'application/vnd.api+json'
  end

  def jsonapi_params
    # Explicitly permit only expected attributes
    # NEVER use .permit! as it allows mass assignment of all attributes
    params.require(:data).require(:attributes).permit(
      :title, :body, :published, :status,
      :email, :name, :password, :password_confirmation,
      tags: [],
      relationships: [:author, :comments]
    )
  end
end

# app/services/json_api_serializer.rb
class JsonApiSerializer
  def initialize(resource, options = {})
    @resource = resource
    @options = options
  end

  def serializable_hash
    if @resource.respond_to?(:map)
      { data: @resource.map { |r| serialize_resource(r) } }
    else
      { data: serialize_resource(@resource) }
    end
  end

  private

  def serialize_resource(resource)
    {
      id: resource.id.to_s,
      type: resource.class.name.underscore.pluralize,
      attributes: resource.as_json(except: [:id, :created_at, :updated_at]),
      relationships: serialize_relationships(resource)
    }
  end

  def serialize_relationships(resource)
    return {} unless @options[:include]
    
    @options[:include].each_with_object({}) do |rel, hash|
      associated = resource.send(rel)
      hash[rel] = {
        data: associated.map { |a| { id: a.id.to_s, type: a.class.name.underscore.pluralize } }
      }
    end
  end
end
```

## Grape API Pattern

```ruby
# app/api/v1/posts.rb
module V1
  class Posts < Grape::API
    version 'v1', using: :path
    format :json
    
    resource :posts do
      desc 'Get all posts'
      get do
        Post.all
      end
      
      desc 'Get a post'
      params do
        requires :id, type: Integer, desc: 'Post ID'
      end
      route_param :id do
        get do
          Post.find(params[:id])
        end
      end
      
      desc 'Create a post'
      params do
        requires :title, type: String, desc: 'Post title'
        requires :body, type: String, desc: 'Post body'
        optional :published, type: Boolean, default: false
      end
      post do
        authenticate!
        Post.create!({
          title: params[:title],
          body: params[:body],
          published: params[:published],
          user: current_user
        })
      end
      
      desc 'Update a post'
      params do
        requires :id, type: Integer
        optional :title, type: String
        optional :body, type: String
        optional :published, type: Boolean
      end
      put ':id' do
        post = Post.find(params[:id])
        authorize! :update, post
        post.update!(declared_params.except(:id))
        post
      end
      
      desc 'Delete a post'
      params do
        requires :id, type: Integer
      end
      delete ':id' do
        post = Post.find(params[:id])
        authorize! :destroy, post
        post.destroy
        { success: true }
      end
    end
  end
end
```

## Jbuilder Pattern

```ruby
# app/views/api/posts/show.json.jbuilder
json.data do
  json.id @post.id
  json.type 'post'
  
  json.attributes do
    json.title @post.title
    json.body @post.body
    json.published @post.published
    json.created_at @post.created_at.iso8601
  end
  
  json.relationships do
    json.author do
      json.data do
        json.id @post.author.id
        json.type 'user'
      end
    end
  end
end

json.included do
  json.array! [@post.author] do |user|
    json.id user.id
    json.type 'user'
    json.attributes do
      json.name user.name
      json.email user.email
    end
  end
end
```

## API Authentication

```ruby
# app/controllers/concerns/api_authentication.rb
module ApiAuthentication
  extend ActiveSupport::Concern

  included do
    before_action :authenticate_request
    attr_reader :current_user
  end

  private

  def authenticate_request
    @current_user = authorize_request
    render json: { error: 'Unauthorized' }, status: :unauthorized unless @current_user
  end

  def authorize_request
    header = request.headers['Authorization']
    header = header.split(' ').last if header
    
    begin
      decoded = JwtService.decode(header)
      User.find(decoded[:user_id])
    rescue ActiveRecord::RecordNotFound, JWT::DecodeError => e
      nil
    end
  end
end

# app/services/jwt_service.rb
class JwtService
  SECRET_KEY = Rails.application.credentials.secret_key_base

  def self.encode(payload, exp = 24.hours.from_now)
    payload[:exp] = exp.to_i
    JWT.encode(payload, SECRET_KEY)
  end

  def self.decode(token)
    decoded = JWT.decode(token, SECRET_KEY)[0]
    HashWithIndifferentAccess.new(decoded)
  rescue JWT::DecodeError => e
    raise e
  end
end
```

## Error Handling

```ruby
# app/controllers/concerns/api_error_handling.rb
module ApiErrorHandling
  extend ActiveSupport::Concern

  included do
    rescue_from StandardError, with: :handle_error
    rescue_from ActiveRecord::RecordNotFound, with: :not_found
    rescue_from ActiveRecord::RecordInvalid, with: :unprocessable
    rescue_from ActionController::ParameterMissing, with: :bad_request
  end

  private

  def handle_error(exception)
    Rails.logger.error(exception.full_message)
    render json: { 
      error: 'Internal Server Error',
      message: Rails.env.production? ? 'Something went wrong' : exception.message
    }, status: :internal_server_error
  end

  def not_found(exception)
    render json: { error: 'Not Found', message: exception.message }, status: :not_found
  end

  def unprocessable(exception)
    render json: { error: 'Unprocessable Entity', message: exception.message }, status: :unprocessable_entity
  end

  def bad_request(exception)
    render json: { error: 'Bad Request', message: exception.message }, status: :bad_request
  end
end
```

## Pagination

```ruby
# app/controllers/api/posts_controller.rb
def index
  @posts = Post.page(params[:page] || 1).per(params[:per_page] || 20)
  
  render json: {
    data: @posts,
    meta: {
      current_page: @posts.current_page,
      next_page: @posts.next_page,
      prev_page: @posts.prev_page,
      total_pages: @posts.total_pages,
      total_count: @posts.total_count
    }
  }
end
```

## Best Practices

### Always Use Strong Parameters

```ruby
# Good: Explicit parameter filtering
def post_params
  params.require(:post).permit(:title, :body, :published, tags: [])
end

# Bad: Mass assignment
def create
  Post.create(params[:post])  # Security risk!
end
```

### Version Your API

```ruby
# config/routes.rb
namespace :api do
  namespace :v1 do
    resources :posts
  end
  
  namespace :v2 do
    resources :posts  # Different implementation
  end
end
```

### Use Proper HTTP Status Codes

```ruby
# 200 OK - Standard response for successful HTTP requests
def index
  render json: Post.all
end

# 201 Created - New resource created
def create
  post = Post.create!(post_params)
  render json: post, status: :created, location: api_post_url(post)
end

# 204 No Content - Successful deletion
def destroy
  @post.destroy
  head :no_content
end

# 400 Bad Request - Malformed request
def create
  render json: { error: 'Invalid JSON' }, status: :bad_request
end

# 401 Unauthorized - Authentication required
def show
  render json: { error: 'Unauthorized' }, status: :unauthorized
end

# 403 Forbidden - Insufficient permissions
def destroy
  render json: { error: 'Forbidden' }, status: :forbidden
end

# 404 Not Found - Resource doesn't exist
def show
  render json: { error: 'Not Found' }, status: :not_found
end

# 422 Unprocessable Entity - Validation errors
def create
  render json: { errors: post.errors }, status: :unprocessable_entity
end
```
