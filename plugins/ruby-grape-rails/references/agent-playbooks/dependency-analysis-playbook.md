# Dependency Analysis Playbook

Use this playbook when `dependency-analyzer` needs deeper examples or command
snippets.

## Unused Methods Detection

```bash
rg -n '^\s*def\s+' app lib
rg -n '\.process_order\b|process_order\(' app lib spec test
rg -n 'define_method|method_missing|public_send|send\(' app lib
```

## Circular Dependency Detection

```ruby
require 'pathname'

files = Dir["app/**/*.rb"]
deps = {}

files.each do |file|
  content = File.read(file)
  deps[file] = content.scan(/require_relative ['"](.+?)['"]/).flatten
end

deps.each do |file, imports|
  imports.each do |imp|
    # Keep everything relative to maintain consistent hash keys
    target_dir = File.dirname(file)
    target = File.join(target_dir, "#{imp}.rb")
    target = Pathname.new(target).cleanpath.to_s
    reverse_edge = Pathname.new(file).relative_path_from(Pathname.new(File.dirname(target))).to_s.delete_suffix(".rb")
    if deps[target]&.include?(reverse_edge)
      puts "Circular: #{file} <-> #{target}"
    end
  end
end
```

## Dependency Graph Sketch

```text
Controllers
├── UsersController
│   └── depends on: UserService, UserPolicy
├── OrdersController
│   └── depends on: OrderService, PaymentService

Services
├── UserService
│   └── depends on: User, UserMailer
├── OrderService
│   └── depends on: Order, PaymentService, InventoryService
```

## Useful Static Checks

```bash
bundle exec rubocop --only Lint/UselessAssignment
bundle exec rubocop --only Lint/UnreachableCode
bundle exec rubocop --only Lint/UnusedMethodArgument
```

## Output Shape

Write findings in three buckets:

1. likely dead code
2. circular or fragile dependency edges
3. coupling hotspots that make refactors risky

For each item, include:

- file or package path
- symbol / constant / edge being discussed
- confidence level
- what evidence was checked
- the next safe action
