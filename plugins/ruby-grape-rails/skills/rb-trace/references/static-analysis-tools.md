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

Use whichever search tool is available (`Grep` tool, `ugrep`, `rg`,
or shell `grep`) — agent picks per the tool-batching preference.
Targets:

- Callers: pattern `UserService\.update|\.update_user` over `app/` Ruby files.
- Caller context: same pattern, request 2 lines before/after.
- Method definitions: pattern `def update_user` over `app/` Ruby files.
- Callers in a single file: pattern `User\.` in
  `app/services/order_service.rb`.

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

Three search passes over Ruby files:

- **Controller actions calling a service**: pattern `UserService\.`
  over `app/controllers` (file-list mode, `-l`-equivalent).
- **Sidekiq jobs calling a method**: pattern `UserService\.update`
  over `app/jobs`.
- **Grape APIs**: pattern `UserService\.` over `app/api`.

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

Search pattern `def user_params` over `app/controllers` Ruby files
to find allowed parameters. Typical pattern:

```ruby
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

Targets:

- ActiveRecord calls: pattern `User\.(find|where|create|update|destroy)`
  over `app/services` Ruby files.
- Caller context (`User\.` in `app/services/order_service.rb`): request
  2 lines before/after.

### Trace Data Flow

Three-step search:

1. Where data enters: pattern `params\[` in
   `app/controllers/users_controller.rb`.
2. Transformations: pattern `def sanitize|def format|def clean` over
   `app/controllers` Ruby files.
3. Usage: pattern `UserService\.create|User\.create` over `app/` Ruby files.

### Check Circular Dependencies

- Gem dependencies: `bundle viz --format png`
- Internal code: search pattern `require.*services` over
  `app/services` Ruby files; aggregate counts via `sort | uniq -c`.

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

# Check if method is private — search pattern `private|def update`
# in `app/services/user_service.rb`.
```

### Too Many Results

- Filter by directory: search pattern `User\.` over `app/services`
  Ruby files, exclude `spec`/`test` paths.
- Focus pattern: `UserService\.(update|create)` over `app/` Ruby files.

### Private Method Calls

Search pattern `\.send\(:update|\.public_send` over `app/` Ruby
files (catches indirect dispatch into private methods).
