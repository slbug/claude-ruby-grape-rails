# Argument Extraction

Extract argument shape and origin from method call sites in Ruby /
Rails / Grape code.

## Goals

| Output | Use |
|---|---|
| Argument names + literal values | Map call shape |
| Variable origins (params, instance vars, DB lookups) | Trace data flow |
| Type / key shape (symbol vs string, hash structure) | Catch mismatches |
| Validation gaps | Surface unsafe input |

## Basic Extraction

### Local-variable arguments

```ruby
def update
  user = User.find(params[:id])
  attrs = sanitize_params(user_params)
  result = UserService.update_user(user, attrs)
  result.success? ? redirect_to(user_path(result.data)) : render(:edit, status: :unprocessable_entity)
end

private

def user_params
  params.require(:user).permit(:name, :email, :role)
end
```

Arguments: `user` (User from `params[:id]`), `attrs` (filtered hash from
strong params).

### Instance-variable arguments

```ruby
def update
  UserService.update_user(@user, user_params)
end
```

`@user` set by `before_action :set_user`. `user_params` filtered hash.

### Sidekiq job arguments

```ruby
class SyncUserJob
  include Sidekiq::Job

  def perform(user_id)
    user = User.find(user_id)
    UserService.sync_user(user)
  end
end
```

`user_id` is the JSON-safe arg; the User instance is fetched per Iron
Law 10 (no ORM objects in args).

### Chained / transformed

```ruby
users.filter_map { |u| UserService.update_user(u, { status: :active }) if u.pending? }
```

First arg = element of `users` collection.

## AST-Based Extraction (Prism)

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
    when Prism::LocalVariableReadNode    then node.name.to_s
    when Prism::InstanceVariableReadNode then node.name.to_s
    when Prism::StringNode               then node.content.inspect
    when Prism::SymbolNode               then ":#{node.value}"
    when Prism::IntegerNode              then node.value.to_s
    else "<complex expression>"
    end
  end
end

ArgumentExtractor.extract_call_args(
  "app/controllers/users_controller.rb",
  45,
  "UserService",
  :update_user
)
```

Returns the literal argument list at that call site (e.g.
`["@user", "user_params"]`).

## Grep-Based Extraction

| Target | Pattern | Scope |
|---|---|---|
| All callers | `UserService\.update_user` (with 2 trailing context lines) | `app/` Ruby |
| Calls with specific arg | `UserService\.create_user.*admin` | `app/` Ruby |
| Argument tuple capture | `UserService\.update_user` piped through `sed 's/.*update_user(\([^)]*\)).*/\1/'` | `app/` Ruby |

Use Prism for accurate AST shape; use grep for fast cross-codebase
pattern detection.

## Recurring Argument Patterns

### Strong params (Rails controller)

```ruby
def user_params
  params.require(:user).permit(:name, :email)
end

def create
  UserService.create_user(user_params)
end
```

Source chain: `params` → `user_params` (filtered) → service.

### Service-object indirection

```ruby
class UserService
  def self.create_user(attrs)
    User.create!(attrs)
  end
end

class UsersController < ApplicationController
  def create
    UserService.create_user(user_params)
  end
end
```

Source chain: `params` → `user_params` (controller) → service →
`User.create!`.

### Grape API params

```ruby
params do
  requires :id, type: Integer
  requires :user, type: Hash do
    optional :name, type: String
  end
end
put ':id' do
  UserService.update_user(params[:id], params[:user])
end
```

Grape coerces and validates; `params` reaches the service already
typed.

## Security Tracing

### Reject raw-params calls (Iron Law 13)

| Form | Verdict |
|---|---|
| `UserService.create_user(params[:user])` | Reject — no permit/require |
| `UserService.create_user(user_params)` | OK — strong params filter |

### Reject SQL string interpolation (Iron Laws 2, 15)

| Form | Verdict |
|---|---|
| `User.where("id = #{user_id}")` | Reject — interpolation |
| `User.where(id: params[:id])` | OK — parameterized |

## Data-Flow Annotation

Document argument origin inline only when the source is non-obvious:

```ruby
def process_order(order_id, user_id)
  order = Order.find(order_id)
  user = User.find(user_id)
  OrderService.process(order, user)
end
```

Origin trace lives in the surrounding code review or call-tracer
report, not as inline narration.

YARD-style param annotation is acceptable for public service methods:

```ruby
# @param user_id [Integer] route constraint validated
# @param attrs [Hash] strong-params filtered
def update_user(user_id, attrs)
  ...
end
```

## Testing Argument Shape

### Strong-params permit assertion

```ruby
RSpec.describe UsersController, type: :controller do
  describe 'POST #create' do
    it 'permits only whitelisted keys' do
      expect_any_instance_of(ActionController::Parameters)
        .to receive(:permit).with(:name, :email, :role)
      post :create, params: { user: { name: 'Test', email: 'test@test.com', admin: true } }
    end
  end
end
```

### Service receives sanitized attrs

```ruby
RSpec.describe UserService do
  describe '.create_user' do
    it 'receives only filtered keys' do
      expect(described_class).to receive(:create_user)
        .with(hash_including(:name, :email))
        .and_call_original
      post users_path, params: { user: { name: 'Test', email: 'test@test.com' } }
    end
  end
end
```

## Tooling

| Tool | Use |
|---|---|
| Prism | AST parsing (built-in Ruby 3.3+) |
| RuboCop | Static pattern detection |
| ripgrep | Fast text search |
| ruby-lsp | IDE call-graph navigation |

## Ruby Gotchas

### Symbol vs string keys

```ruby
params[:user]              # ActionController::Parameters indifferent access
params["user"]             # also works
params.require(:user).permit(:name, :email)
```

Plain `Hash` is NOT indifferent; convert via `.with_indifferent_access`
when needed.

### Implicit nil return

```ruby
def find_user(id)
  User.find_by(id: id)
end
```

Prefer this over explicit `return nil`. `find_by` already returns nil
on miss.

### Safe-navigation chains

```ruby
user&.address&.city
```

Use safe navigation for nullable chains; do NOT chain past confirmed
non-nil values.
