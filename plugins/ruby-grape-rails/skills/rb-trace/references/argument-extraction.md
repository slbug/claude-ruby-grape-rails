# Argument Extraction

Techniques for extracting argument patterns from method call sites in Ruby/Rails/Grape applications.

## Why Arguments Matter

Knowing "who calls" isn't enough. **HOW** they call reveals:

- Data flow through the system
- Where nil values originate
- Pattern mismatches (symbol vs string keys)
- Missing validations
- Security vulnerabilities

## Basic Extraction

### From Call Site Line

```ruby
# Call site: app/controllers/users_controller.rb:45
UserService.update_user(user, attrs)

# Extract:
# Arg 1: `user` - local variable (User instance)
# Arg 2: `attrs` - local variable (Hash)

# Need to trace where these variables come from in the same method
```

### Trace Variable Origins

```ruby
def update
  user = User.find(params[:id])        # <- user comes from DB query
  attrs = sanitize_params(user_params) # <- attrs comes from params + transform

  result = UserService.update_user(user, attrs)  # <- call site
  if result.success?
    redirect_to user_path(result.data)
  else
    render :edit, status: :unprocessable_entity
  end
end

# Full trace:
# user = User.find(params[:id]) where id = params[:id] (string from URL!)
# attrs = sanitize_params(user_params) where user_params = params.require(:user)
```

## Common Argument Patterns

### Direct from Params (Rails Controller)

```ruby
def create
  UserService.create_user(user_params)
  #                   ^^^^^^^^^^^
  # Source: params[:user] (strong params required!)
end

private

def user_params
  params.require(:user).permit(:name, :email, :role)
end
```

### From Instance Variables (Controllers)

```ruby
def update
  # @user set in before_action
  UserService.update_user(@user, user_params)
  #                   ^^^^^   ^^^^^^^^^^^
  # Source 1: @user (set in set_user callback)
  # Source 2: strong params (filtered hash)
end
```

### From Job Args (Sidekiq)

```ruby
class SyncUserJob
  include Sidekiq::Job
  
  def perform(user_id)  # <- JSON-safe argument
    user = User.find(user_id)
    UserService.sync_user(user)
    #                  ^^^^
    # Source: DB query using job args["user_id"]
  end
end
```

### Chained/Transformed

```ruby
users
  .filter_map { |u| UserService.update_user(u, { status: :active }) if u.pending? }
#                                   ^^
# Source: element from `users` collection
```

## AST-Based Extraction (Advanced)

Using Prism parser (Ruby 3.3+ standard):

```ruby
require 'prism'

class ArgumentExtractor
  def self.extract_call_args(file_path, line, target_class, target_method)
    source = File.read(file_path)
    result = Prism.parse(source)
    
    visitor = CallVisitor.new(line, target_class, target_method)
    visitor.visit(result.value)
    visitor.arguments
  end
end

class CallVisitor < Prism::Visitor
  def initialize(target_line, target_class, target_method)
    @target_line = target_line
    @target_class = target_class
    @target_method = target_method
    @arguments = nil
  end
  
  attr_reader :arguments
  
  def visit_call_node(node)
    if node.location.start_line == @target_line &&
       node.receiver&.name == @target_class &&
       node.name == @target_method
      @arguments = node.arguments.arguments.map { |arg| arg_to_string(arg) }
    end
    super
  end
  
  private
  
  def arg_to_string(node)
    case node
    when Prism::LocalVariableReadNode
      node.name.to_s
    when Prism::InstanceVariableReadNode
      node.name.to_s
    when Prism::StringNode
      node.content.inspect
    when Prism::SymbolNode
      ":#{node.value}"
    when Prism::IntegerNode
      node.value.to_s
    else
      "<complex expression>"
    end
  end
end

# Usage
ArgumentExtractor.extract_call_args(
  "app/controllers/users_controller.rb",
  45,
  "UserService",
  :update_user
)
# => ["@user", "user_params"]
```

## Grep-Based Extraction (Simpler)

When AST parsing is overkill:

```bash
# Find all calls to a method
rg "UserService\.update_user" app/ --type ruby -A 2

# Find calls with specific arguments
rg "UserService\.create_user.*admin" app/ --type ruby

# Extract variable names passed to method
grep -rn "UserService\.update_user" app/ --include="*.rb" | \
  sed 's/.*update_user(\([^)]*\)).*/\1/'
```

## Pattern Recognition

### Strong Parameters Pattern

```ruby
# app/controllers/users_controller.rb
def user_params
  # This pattern filters params
  params.require(:user).permit(:name, :email)
end

def create
  # Traces to: params[:user] (but filtered!)
  UserService.create_user(user_params)
end
```

### Service Object Pattern

```ruby
# app/services/user_service.rb
class UserService
  def self.create_user(attrs)
    # attrs comes from controller (already sanitized)
    User.create!(attrs)
  end
end

# In controller
def create
  # Argument trace: params -> user_params -> UserService.create_user
  UserService.create_user(user_params)
end
```

### Grape API Params Pattern

```ruby
# app/api/v1/users.rb
params do
  requires :id, type: Integer
  requires :user, type: Hash do
    optional :name, type: String
  end
end
put ':id' do
  # Traces to: params[:user] (validated and coerced)
  UserService.update_user(params[:id], params[:user])
end
```

## Security Tracing

### Finding Insecure Parameter Passing

```ruby
# BAD: Raw params passed through
def create
  UserService.create_user(params[:user])  # No validation!
end

# GOOD: Strong params
# Traces through: params -> user_params (permitted) -> service

def create
  UserService.create_user(user_params)
end
```

### SQL Injection Tracing

```ruby
# BAD: User input interpolated in SQL
user_id = params[:id]
User.where("id = #{user_id}")  # DANGEROUS!

# GOOD: Parameterized
User.where(id: params[:id])     # Safe
```

## Data Flow Documentation

### Annotating Call Sites

```ruby
def process_order(order_id, user_id)
  # DATA FLOW:
  # order_id -> from params[:order_id] (string, validated as integer)
  # user_id  -> from current_user.id (integer, from session)
  
  order = Order.find(order_id)
  user = User.find(user_id)
  
  OrderService.process(order, user)
end
```

### Using Method Comments

```ruby
# @param user_id [Integer] from params[:id], validated by route constraint
# @param attrs [Hash] from user_params (strong params, see #user_params)
# @return [Result<User>] success with user or failure with errors
def update_user(user_id, attrs)
  # ...
end
```

## Testing Argument Patterns

### Verifying Strong Parameters

```ruby
RSpec.describe UsersController, type: :controller do
  describe 'POST #create' do
    it 'only permits whitelisted params' do
      expect_any_instance_of(ActionController::Parameters)
        .to receive(:permit).with(:name, :email, :role)
      
      post :create, params: { user: { name: 'Test', email: 'test@test.com', admin: true } }
    end
  end
end
```

### Testing Data Flow

```ruby
RSpec.describe UserService do
  describe '.create_user' do
    it 'receives sanitized attributes' do
      # Ensure service never gets raw params
      expect(described_class).to receive(:create_user)
        .with(hash_including(:name, :email))
        .and_call_original
      
      post users_path, params: { user: { name: 'Test', email: 'test@test.com' } }
    end
  end
end
```

## Tools for Argument Analysis

| Tool | Use For |
|------|---------|
| Prism | Ruby AST parsing (built-in 3.3+) |
| RuboCop | Static analysis, pattern detection |
| rg (ripgrep) | Fast text search across codebase |
| Ruby-lsp | IDE integration, go-to-definition |

## Common Ruby Gotchas

### Symbol vs String Keys

```ruby
# Rails params come as string keys
params[:user]        # Works (Rails indifferent access)
params["user"]       # Also works

# But be careful with nested access
params[:user][:name]        # Works
params[:user]["name"]       # Might fail if using regular Hash

# Always use strong params
def user_params
  params.require(:user).permit(:name, :email)  # Returns ActionController::Parameters
end
```

### Implicit vs Explicit nil

```ruby
# BAD: Explicit nil return
def find_user(id)
  user = User.find_by(id: id)
  return nil unless user
  user
end

# GOOD: Implicit nil
def find_user(id)
  user = User.find_by(id: id)
  return unless user
  user
end

# BETTER: Just let it flow
def find_user(id)
  User.find_by(id: id)  # Returns nil if not found
end
```

### Safe Navigation Operator

```ruby
# Before Ruby 2.3
user && user.address && user.address.city

# Modern Ruby
user&.address&.city
```
