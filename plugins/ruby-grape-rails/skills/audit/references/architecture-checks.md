# Architecture Checks Reference

Detailed criteria for architecture health assessment in Ruby/Rails/Grape applications.

## Service Object Health Matrix

### What to Check

For each service in `app/services/` or domain module:

| Metric | Healthy Range | Red Flag |
|--------|---------------|----------|
| Classes per service | 3-15 | >20 or <2 |
| Public API methods | 5-30 | >40 |
| Models per service | 1-5 | >8 |
| Fan-out (services called) | 1-4 | >6 |
| Fan-in (called by services) | 1-6 | >10 |

### Commands

Metrics:

- **Class count per service directory**: count Ruby files per
  subdirectory under `app/services/`.
- **Public method count**: count matches of pattern
  `^  def [a-z]` over `app/services` Ruby files.
- **Model count**: count Ruby files at `app/models/` depth 1.
- **Dependency analysis from `Gemfile.lock`**:

```ruby
require 'bundler'
puts Bundler::LockfileParser.new(Bundler.read_file('Gemfile.lock')).dependencies.keys.sort
```

## Coupling Analysis

### Fan-Out (Efferent Coupling)

How many other services does this service depend on?

For each service, count outgoing dependencies. Search `app/services`
Ruby files; count matches of patterns like `UserService\.`,
`OrderService\.`, etc., per outgoing target service.

| Fan-Out | Assessment |
|---------|------------|
| 0-2 | Excellent - well isolated |
| 3-4 | Good - reasonable dependencies |
| 5-6 | Warning - consider splitting |
| 7+ | Critical - "god service" |

### Fan-In (Afferent Coupling)

How many services depend on this service?

| Fan-In | Assessment |
|--------|------------|
| 0 | Dead code? Or utility only |
| 1-4 | Good - clear responsibility |
| 5-8 | Common utility - ensure stable API |
| 9+ | Core abstraction - avoid changes |

## Cohesion Analysis

### Signs of Low Cohesion

- Service name is generic ("Utils", "Helpers", "Services", "Common")
- Methods don't share domain vocabulary
- Multiple unrelated models in same service
- Service has >50 public methods

### Assessment

Two checks:

- **Generic names**: list `app/services/` entries; flag those
  matching pattern `utils|helpers|services|common|shared|misc`
  (case-insensitive).
- **Large API surface**: per `.rb` file under `app/services/`,
  count matches of pattern `^  def [a-z]`. Flag any file with > 30
  public methods.

## Boundary Violations

### Types of Violations

| Violation | Severity | Example |
|-----------|----------|---------|
| Direct DB queries from controller | High | `User.all` in controller |
| Cross-service model access | Medium | `OrderService` uses `User` model |
| Direct model instantiation | Low | `User.new` outside service |
| Service calling view layer | High | Business logic → presentation |

### Detection

Three searches over Ruby files:

- **Direct ActiveRecord calls in controllers/views**: pattern
  `Model\.(all|where|find|create)` over `app/controllers` and
  `app/views`.
- **Cross-service model usage**: pattern `User\.|User::` in
  `app/services/order_service.rb`.
- **Views calling business logic**: pattern `Service\.` over
  `app/views`.

## Ruby/Rails-Specific Patterns

### Healthy Directory Structure

```
app/
  controllers/
    api/v1/          # API controllers
    admin/           # Admin controllers
  services/
    user_service.rb
    order_service.rb
  models/
    concerns/        # Shared model behavior
  queries/
    user_query.rb
  decorators/
    user_decorator.rb
  policies/
    user_policy.rb
```

### Service Object Pattern Assessment

Single responsibility — each service owns one domain noun:

```ruby
class UserService
  def self.create(attrs)
    User.create!(attrs)
  end

  def self.find(id)
    User.find(id)
  end
end
```

Reject god-services that absorb unrelated responsibilities (auth,
import/export, reporting):

```ruby
class UserManager
  def create_user(attrs); end
  def reset_password(user); end
  def export_users; end
  def import_users; end
  def generate_report; end
end
```

### Grape API Organization

One resource per file. Mount versioned resource classes from a base
API:

```ruby
class API < Grape::API
  mount V1::Users
  mount V1::Orders
end

module V1
  class Users < Grape::API
    resource :users do
      get  { User.all }
      post { User.create!(declared_params) }
    end
  end
end
```

## Modern Ruby 3.4+ Patterns (2026)

### Data classes for value objects (Ruby 3.2+)

```ruby
Coordinate = Data.define(:latitude, :longitude) do
  def to_s
    "#{latitude},#{longitude}"
  end
end

coord = Coordinate.new(40.7128, -74.0060)
coord.latitude  # => 40.7128
```

### Pattern Matching for Complex Logic

```ruby
def handle_result(result)
  case result
  in { success: true, data: { user: User => user } }
    redirect_to user_path(user)
  in { success: false, error: :not_found }
    render_404
  in { success: false, error: :unauthorized }
    render_403
  else
    render_error
  end
end
```

### `it` keyword for short blocks (Ruby 3.4+)

```ruby
users.map { it.name }
posts.filter_map { it.title if it.published? }
```

## Tooling for Architecture Analysis

### RuboCop with custom architectural cops

```yaml
require:
  - rubocop-rails
  - rubocop-performance
  - ./lib/custom_cops/architecture_cops.rb

AllCops:
  NewCops: enable

Custom/NoDirectDbInController:
  Enabled: true
  Include:
    - app/controllers/**/*.rb
```

`Custom/NoDirectDbInController` rejects direct model calls inside the
controller layer.

### Using Pronto for CI

```yaml
# Example dedicated workflow (or add these steps to an existing workflow)
- name: Check Architecture
  run: |
    pronto run --runner architecture
    bundle exec rake architecture:check
```

### Ruby-Next for back-port runtime support

```ruby
gem 'ruby-next', require: false
```

```ruby
require 'ruby-next/language/runtime'
```

Enables Ruby 3.4 syntax on older runtimes; out of scope for this
plugin's own code (3.4+ floor) but acceptable in projects pinned to
older Ruby.

## Metrics Calculation

### Service complexity rake task

```ruby
namespace :architecture do
  desc "Calculate service complexity metrics"
  task analyze: :environment do
    Dir["app/services/*.rb"].each do |file|
      content = File.read(file)
      methods = content.scan(/^  def [a-z]/).count
      lines   = content.lines.count

      puts "#{File.basename(file)}:"
      puts "  Public methods: #{methods}"
      puts "  Total lines:    #{lines}"
      puts "  Ratio:          #{(lines.to_f / methods).round(2)} lines/method"
      puts
    end
  end
end
```

### Check Dependency Graph

- **Gem dependency summary** from `Gemfile.lock`:

  ```ruby
  require 'bundler'
  puts Bundler::LockfileParser.new(Bundler.read_file('Gemfile.lock')).dependencies.keys.sort
  ```

- **Internal dependencies** (search Ruby files):
  - pattern `require.*services/` over `app`
  - pattern `include.*Concern` over `app/models`

## Refactoring Checklist

- [ ] Services have single responsibility
- [ ] No generic names (Utils, Helpers, etc.)
- [ ] Controllers delegate to services (no direct DB calls)
- [ ] Models handle persistence only (no business logic)
- [ ] Fan-out < 4 for each service
- [ ] Fan-in < 8 for utility services
- [ ] Methods per service < 30
- [ ] Clear domain vocabulary in each service
