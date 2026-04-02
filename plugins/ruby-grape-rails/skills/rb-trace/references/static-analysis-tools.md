# Ruby Call Tracing and Static Analysis Reference

Complete reference for tracing method calls in Ruby/Rails/Grape applications using modern 2026 tooling.

## Tool Overview

| Tool | Purpose | Modern Alternative (2026) |
|------|---------|---------------------------|
| Ripper | Ruby parser (stdlib) | Prism (faster, better errors) |
| `caller_locations` | Runtime call stack | Built-in, still relevant |
| RuboCop AST | Static analysis | RuboCop with plugins |
| sorbet-static | Type checking | Steep or Sorbet |
| grep/ripgrep | Text search | Still essential |

## Prism Parser (Ruby 3.3+ Standard)

Prism is the new default Ruby parser, replacing Ripper:

```ruby
require 'prism'

# Parse Ruby code
source = <<~RUBY
  class UserController < ApplicationController
    def update
      user = User.find(params[:id])
      user.update!(user_params)
    end
  end
RUBY

result = Prism.parse(source)

# Walk the AST
class CallFinder < Prism::Visitor
  def initialize
    @calls = []
  end
  
  def visit_call_node(node)
    @calls << node.name
    super
  end
end

finder = CallFinder.new
finder.visit(result.value)
finder.calls  # => [:find, :update!]
```

## Runtime Call Tracing

### Using caller_locations

```ruby
# Debug who called a method
def update_user(user_id, attrs)
  # Log the call stack
  puts "Called from: #{caller_locations(1..5).map(&:to_s).join("\n")}"
  
  User.find(user_id).update!(attrs)
end

# Find specific callers
def find_callers_of(target_method)
  ObjectSpace.each_object(Method).select do |method|
    method.source_location && method.name == target_method
  end
end
```

### Using TracePoint

```ruby
# Trace all method calls
trace = TracePoint.new(:call, :c_call) do |tp|
  if tp.defined_class == User && tp.method_id == :update!
    puts "#{tp.path}:#{tp.lineno}: #{tp.defined_class}##{tp.method_id}"
  end
end

trace.enable do
  # Code to trace
  User.first.update!(name: "Test")
end
```

## Static Analysis with RuboCop

### Finding All Callers

```bash
# Find who calls a specific method using grep/ripgrep
rg "UserService\.update\|\.update_user" app/ --type ruby

# With context (show surrounding lines)
rg -B 2 -A 2 "UserService\.update" app/ --type ruby

# Find method definitions
grep -rn "def update_user" app/ --include="*.rb"

# Find all calls in a file
rg "User\." app/services/order_service.rb --type ruby
```

### Custom RuboCop Cop for Call Tracing

```ruby
# lib/rubocop/cop/custom/call_tracer.rb
module RuboCop
  module Cop
    module Custom
      class CallTracer < Base
        MSG = 'Method `%<method>s` called on `%<receiver>s`.'
        
        def_node_matcher :method_call, <<~PATTERN
          (send $_ $_ ...)
        PATTERN
        
        def on_send(node)
          receiver, method = method_call(node)
          return unless receiver
          
          if receiver.const_name == 'UserService' && method == :update
            add_offense(node, message: format(MSG, method: method, receiver: receiver.const_name))
          end
        end
      end
    end
  end
end
```

## Modern Call Graph Analysis (2026)

### Using steep for Type-Based Analysis

```yaml
# Steepfile
target :app do
  check "app/**/*.rb"
  library "activerecord"
  library "actionpack"
end
```

```ruby
# Type signatures help trace calls
# sig/app/services/user_service.rbs
class UserService
  def self.update: (Integer, Hash[Symbol, untyped]) -> User
  def self.find: (Integer) -> User
  def self.list: -> Array[User]
end
```

### Rails-Specific Tools

```bash
# Find all controller actions that call a service
rg "UserService\." app/controllers --type ruby -l

# Find all Sidekiq jobs that call a method
rg "UserService\.update" app/jobs --type ruby

# Trace through Grape APIs
rg "UserService\." app/api --type ruby
```

## Argument Extraction Patterns

### From Call Sites

```ruby
# Call site: app/controllers/users_controller.rb:45
UserService.update(user, attrs)

# Extract:
# Arg 1: `user` - local variable
# Arg 2: `attrs` - local variable

# Find origins:
# user = User.find(params[:id])  <- from DB
# attrs = user_params            <- from params (strong params)
```

### Strong Parameters Tracing

```ruby
# Find what parameters are allowed
grep -rn "def user_params" app/controllers --include="*.rb"

# Typical pattern:
def user_params
  params.require(:user).permit(:name, :email, :role)
end
```

### Grape API Parameter Tracing

```ruby
# app/api/v1/users.rb
params do
  requires :id, type: Integer
  requires :user, type: Hash do
    optional :name, type: String
    optional :email, type: String
  end
end
put ':id' do
  UserService.update(params[:id], params[:user])
end
```

## Integration with Pronto (2026)

Pronto runs analysis on changed files in CI:

```yaml
# Example workflow file in your app repo: .github/workflows/pronto.yml
name: Pronto
on: [pull_request]

jobs:
  pronto:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.4'
          bundler-cache: true
      
      - run: bundle exec pronto run -f github_pr -c origin/${{ github.base_ref }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

```ruby
# Gemfile
group :development do
  gem 'pronto'
  gem 'pronto-rubocop'
  gem 'pronto-flay'      # Detect code duplication
  gem 'pronto-reek'      # Code smell detection
  gem 'pronto-brakeman'  # Security analysis
end
```

## Flay for Duplication Detection

```bash
# Install flay
gem install flay

# Run on your codebase
flay app/

# Output:
# app/services/user_service.rb:15
# app/services/admin/user_service.rb:20
# Similar code found in :update (mass = 156)
```

## Dependency Graph Analysis

### Using bundler-leak

```bash
# Check for memory leak vulnerabilities in gems
gem install bundler-leak
bundle leak check

# Check for outdated gems with known issues
bundle audit
```

### Using import_map for JS Dependencies

```bash
# Pin JavaScript dependencies in Rails 8+
bin/importmap pin stimulus
bin/importmap pin @hotwired/turbo
```

## Practical Examples

### Find All Database Calls in a Service

```bash
# Find ActiveRecord calls
rg "User\.(find|where|create|update|destroy)" app/services --type ruby

# With context
rg -B 2 -A 2 "User\." app/services/order_service.rb --type ruby
```

### Trace Data Flow

```bash
# Step 1: Find where data enters
rg "params\[" app/controllers/users_controller.rb --type ruby

# Step 2: Find transformations
grep -rn "def sanitize\|def format\|def clean" app/controllers --include="*.rb"

# Step 3: Find where it's used
rg "UserService\.create\|User\.create" app/ --type ruby
```

### Check Circular Dependencies

```bash
# Use bundler to check gem dependencies
bundle viz --format png

# For internal code, use grep
rg "require.*services" app/services --type ruby | sort | uniq -c
```

## Modern Ruby 3.4+ Tracing

```ruby
# Use Data.define for immutable call records
CallSite = Data.define(:file, :line, :method, :receiver, :args)

# Trace with pattern matching
def trace_calls(&block)
  calls = []
  
  trace = TracePoint.new(:call) do |tp|
    calls << CallSite.new(
      file: tp.path,
      line: tp.lineno,
      method: tp.method_id,
      receiver: tp.defined_class,
      args: tp.parameters
    )
  end
  
  trace.enable(&block)
  calls
end

# Usage
calls = trace_calls { UserService.update(1, { name: "Test" }) }
calls.each { |c| puts "#{c.file}:#{c.line}: #{c.receiver}##{c.method}" }
```

## Common Issues

### "Method not found"

```bash
# Ensure Rails is loaded
bundle exec rails runner "puts UserService.instance_methods(false)"

# Check if method is private
grep -n "private\|def update" app/services/user_service.rb
```

### Too Many Results

```bash
# Filter by directory
rg "User\." app/services --type ruby | grep -v "spec\|test"

# Focus on specific pattern
rg "UserService\.(update|create)" app/ --type ruby
```

### Private Method Calls

```bash
# Grep for send calls (calling private methods)
rg "\.send\(:update\|\.public_send" app/ --type ruby
```
