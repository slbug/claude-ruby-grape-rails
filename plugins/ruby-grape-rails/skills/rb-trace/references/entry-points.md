# Entry Points Reference

Patterns for identifying entry points in Ruby/Rails/Grape applications. These are where request/event handling begins - stop tracing here.

## Rails Controllers

### Standard REST Actions

```ruby
class UsersController < ApplicationController
  # Entry points for HTTP requests
  def index      # GET /users
  def show       # GET /users/:id
  def new        # GET /users/new
  def create     # POST /users
  def edit       # GET /users/:id/edit
  def update     # PATCH/PUT /users/:id
  def destroy    # DELETE /users/:id
  
  # Custom actions
  def search     # GET /users/search
  def export     # GET /users/export
end
```

**Detection pattern:**

```regex
def (index|show|new|create|edit|update|destroy|\w+)\s*($|\s|#)
```

**Entry point info:**

- Route: Check `config/routes.rb` for matching path
- HTTP method: GET/POST/PUT/PATCH/DELETE
- Params come from: URL params (`params[:id]`), query string, request body (JSON/form-data)
- Strong params required: Use `params.require(:user).permit(...)`

### API Controllers (Rails API Mode)

```ruby
module Api
  class UsersController < ApplicationController
    # No CSRF token in API mode
    skip_before_action :verify_authenticity_token
    
    def index
      @users = User.all
      render json: @users
    end
    
    def create
      @user = User.new(user_params)
      if @user.save
        render json: @user, status: :created
      else
        render json: { errors: @user.errors }, status: :unprocessable_entity
      end
    end
  end
end
```

## Grape API Entry Points

### Standalone Grape API

```ruby
# app/api/base.rb
class API < Grape::API
  version 'v1', using: :path
  format :json
  
  resource :users do
    desc 'Get all users'
    get do  # Entry point: GET /api/v1/users
      User.all
    end
    
    desc 'Get a user'
    params { requires :id, type: Integer }
    get ':id' do  # Entry point: GET /api/v1/users/:id
      User.find(params[:id])
    end
    
    desc 'Create a user'
    params do
      requires :name, type: String
      requires :email, type: String
    end
    post do  # Entry point: POST /api/v1/users
      User.create!(declared_params)
    end
    
    desc 'Update a user'
    params do
      requires :id, type: Integer
      optional :name, type: String
      optional :email, type: String
    end
    put ':id' do  # Entry point: PUT /api/v1/users/:id
      user = User.find(params[:id])
      user.update!(declared_params.except(:id))
      user
    end
    
    desc 'Delete a user'
    params { requires :id, type: Integer }
    delete ':id' do  # Entry point: DELETE /api/v1/users/:id
      User.find(params[:id]).destroy
      { success: true }
    end
  end
end
```

### Grape Inside Rails

```ruby
# config/routes.rb
Rails.application.routes.draw do
  mount API => '/api'
end

# app/api/v1/users.rb
module V1
  class Users < Grape::API
    namespace :users do
      get do
        current_organization.users
      end
      
      route_param :id do
        get do
          User.find(params[:id])
        end
        
        put do
          UserService.update(params[:id], declared_params)
        end
      end
    end
  end
end
```

**Detection patterns:**

```regex
^(get|post|put|patch|delete)\s+['"]?[\w\/:\.]+['"]?\s+do
```

**Entry point info:**

- Defined by: HTTP verb + path combination
- Params: Validated and coerced via `params` block
- Auth: Use `before` hooks or `doorkeeper`/`jwt` gems
- Error handling: `rescue_from` in Grape API class

## Sidekiq Jobs

### Standard Job Entry Points

```ruby
# app/jobs/email_job.rb
class EmailJob
  include Sidekiq::Job
  
  # Entry point: Sidekiq calls this method
  def perform(user_id, email_type)
    user = User.find(user_id)
    UserMailer.with(user: user).send(email_type).deliver_now
  end
end

# Alternative with options
class ExportJob
  include Sidekiq::Job
  sidekiq_options queue: 'exports', retry: 3
  
  def perform(export_id)
    export = Export.find(export_id)
    export.process!
  end
end
```

**Detection pattern:**

```regex
class.*Job\n.*include Sidekiq::Job\n.*def perform\(
```

**Entry point info:**

- Triggered by: `EmailWorker.perform_async(args)` or `EmailWorker.perform_in(5.minutes, args)`
- Args: JSON-serializable only (no symbols, no Ruby objects)
- Context: No HTTP context, no current_user - pass IDs only
- Retry: Configured via `sidekiq_options`

### ActiveJob (Rails abstraction)

```ruby
# app/jobs/send_email_job.rb
class SendEmailJob < ApplicationJob
  queue_as :default
  
  def perform(user, email_type)  # Entry point
    UserMailer.with(user: user).send(email_type).deliver_now
  end
end

# Enqueue
SendEmailJob.perform_later(user, 'welcome')
SendEmailJob.perform_now(user, 'welcome')  # Sync
```

## Rake Tasks

### Standard Rake Task Entry Points

```ruby
# lib/tasks/users.rake
namespace :users do
  desc "Import users from CSV"
  task import: :environment do  # Entry point
    CSV.foreach('users.csv', headers: true) do |row|
      User.create!(row.to_h)
    end
  end
  
  desc "Export users to JSON"
  task export: :environment do  # Entry point
    users = User.all.as_json
    File.write('users.json', users.to_json)
  end
  
  desc "Clean up inactive users"
  task cleanup: :environment do  # Entry point
    User.inactive.destroy_all
  end
end
```

**Detection pattern:**

```regex
task\s+\w+:\s*:environment\s+do
```

**Entry point info:**

- Triggered by: `bundle exec rake users:import`
- Env: Full Rails environment loaded (`:environment` dependency)
- Params: Use ENV vars or command line args
- No HTTP context

## Rails Initializers

```ruby
# config/initializers/cache_setup.rb
Rails.application.config.after_initialize do
  # Entry point: Runs after Rails boots
  Rails.cache.clear if Rails.env.development?
end

# config/initializers/sidekiq.rb
Sidekiq.configure_server do |config|
  # Entry point: Runs when Sidekiq starts
  config.redis = { url: ENV['REDIS_URL'] }
end
```

## Event Listeners / Webhooks

### Stripe Webhook

```ruby
# app/controllers/webhooks/stripe_controller.rb
class Webhooks::StripeController < ApplicationController
  skip_before_action :verify_authenticity_token
  
  def create  # Entry point: POST /webhooks/stripe
    payload = request.body.read
    event = Stripe::Webhook.construct_event(payload, sig_header, webhook_secret)
    
    case event.type
    when 'invoice.payment_succeeded'
      handle_payment_success(event.data.object)
    when 'customer.subscription.deleted'
      handle_subscription_cancelled(event.data.object)
    end
    
    head :ok
  end
end
```

### Pub/Sub with ActionCable

```ruby
# app/channels/notifications_channel.rb
class NotificationsChannel < ApplicationCable::Channel
  def subscribed  # Entry point: Client subscribes
    stream_for current_user
  end
  
  def receive(data)  # Entry point: Client sends message
    # Process client message
  end
  
  def unsubscribed  # Entry point: Client disconnects
    # Cleanup
  end
end
```

## Middleware Entry Points

### Rack Middleware

```ruby
# app/middleware/request_timer.rb
class RequestTimer
  def initialize(app)
    @app = app
  end
  
  def call(env)  # Entry point: Every request
    start = Time.current
    status, headers, body = @app.call(env)
    duration = Time.current - start
    
    Rails.logger.info "#{env['REQUEST_METHOD']} #{env['PATH_INFO']} - #{duration.round(3)}s"
    
    [status, headers, body]
  end
end
```

### Rails Controller Callbacks

```ruby
class ApplicationController < ActionController::Base
  before_action :authenticate_user!  # Entry point before actions
  before_action :set_current_organization
  
  around_action :track_performance
  
  private
  
  def track_performance
    # Entry point: Wraps action execution
    start = Time.current
    yield
    Rails.logger.info "Action took #{Time.current - start}s"
  end
end
```

## Testing Entry Points

### RSpec

```ruby
# spec/requests/users_spec.rb
RSpec.describe "Users", type: :request do
  describe "GET /users" do
    it "returns all users" do
      get users_path  # Entry point simulation
      expect(response).to have_http_status(:ok)
    end
  end
end

# spec/workers/email_worker_spec.rb
RSpec.describe EmailWorker, type: :worker do
  it "sends an email" do
    user = create(:user)
    EmailWorker.new.perform(user.id, 'welcome')  # Entry point simulation
    expect(ActionMailer::Base.deliveries.count).to eq(1)
  end
end
```

### Minitest

```ruby
# test/controllers/users_controller_test.rb
class UsersControllerTest < ActionDispatch::IntegrationTest
  test "should get index" do
    get users_url  # Entry point simulation
    assert_response :success
  end
end
```

## Summary: When to Stop Tracing

| Component | Entry Point Pattern | Stop Tracing When |
|-----------|----------------------|-------------------|
| Rails Controller | `def action_name` | Controller action starts |
| Grape API | `get/post/put/delete do` | Grape endpoint starts |
| Sidekiq Worker | `def perform(args)` | Worker.perform called |
| Rake Task | `task name: :environment` | Task invoked |
| ActionCable | `def subscribed/receive` | Channel method called |
| Webhook | `def create` | Webhook receives payload |
| Middleware | `def call(env)` | Request enters middleware |
| Initializer | `Rails.application.config.after_initialize` | Rails boots |

## Modern 2026 Tools

| Tool | Use For |
|------|---------|
| Prism | Ruby AST parsing (built-in 3.3+) |
| Ripper | Legacy AST parsing |
| `TracePoint` | Runtime call tracing |
| `caller_locations` | Stack trace analysis |
| `bundle viz` | Gem dependency graph |
| `bin/importmap` | JS dependency tracing |
