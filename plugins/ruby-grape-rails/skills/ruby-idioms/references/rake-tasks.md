# Rake Task Patterns

> **Official docs**: <https://ruby.github.io/rake/>
> **Rails guides**: <https://guides.rubyonrails.org/command_line.html#rake>

## Task Naming Convention

Rake task names map directly to the CLI command:

```ruby
# lib/tasks/my_app.rake
namespace :my_app do
  desc "Validate configuration"
  task validate: :environment do
    # Do work here
    puts "Validating configuration..."
    
    if valid?
      puts "✓ Configuration is valid"
    else
      puts "✗ Configuration has errors"
      exit 1
    end
  end
  
  desc "Import data from CSV"
  task import: :environment do
    # Task implementation
  end
end

# Usage:
# bundle exec rake my_app:validate
# bundle exec rake my_app:import
```

**Rules:**

- Use `desc` for task description (shows in `rake -T`)
- Namespaced tasks avoid conflicts
- `:environment` dependency loads Rails
- Exit with non-zero status on failure

## Option Parsing

```ruby
# lib/tasks/my_app.rake
namespace :my_app do
  desc "Process files with options"
  task :process, [:type, :format] => :environment do |t, args|
    # Positional args
    type = args[:type] || "default"
    format = args[:format] || "json"
    
    puts "Processing with type=#{type}, format=#{format}"
  end
  
  desc "Process with ENV options"
  task process_env: :environment do
    # Environment-based options
    dry_run = ENV["DRY_RUN"] == "true"
    verbose = ENV["VERBOSE"] == "true"
    
    puts "Dry run: #{dry_run}"
    puts "Verbose: #{verbose}"
  end
end

# Usage:
# bundle exec rake my_app:process[csv,xml]
# DRY_RUN=true VERBOSE=true bundle exec rake my_app:process_env
```

## Shell Output

```ruby
# Use puts/print for output
puts "Processing #{count} items..."
puts "✓ All checks passed".green if defined?(String.colors)

# For colored output, use ANSI or colorize gem
namespace :my_app do
  task status: :environment do
    puts "\e[32m✓\e[0m Application is running"
    puts "\e[31m✗\e[0m Database connection failed"
  end
end

# Progress reporting
namespace :import do
  task users: :environment do
    total = User.count
    User.find_each.with_index do |user, index|
      process_user(user)
      print "\rProcessing #{index + 1}/#{total}"
    end
    puts "\nDone!"
  end
end
```

## Chaining Tasks

```ruby
# Run dependencies before task
namespace :deploy do
  task preflight: :environment do
    puts "Running preflight checks..."
    # Check migrations are present
    # Check environment variables
  end
  
  task migrate: :environment do
    puts "Running migrations..."
    ActiveRecord::Migrator.migrate("db/migrate")
  end
  
  task seed: :environment do
    puts "Seeding data..."
    Rails.application.load_seed
  end
  
  desc "Full deployment process"
  task full: [:preflight, :migrate, :seed] do
    puts "Deployment complete!"
  end
end

# Usage:
# bundle exec rake deploy:full
```

## Task Complexity

Rake tasks often grow complex. Split into methods:

```ruby
# lib/tasks/data_cleanup.rake
namespace :data do
  desc "Clean up orphaned records"
  task cleanup: :environment do
    cleanup_orphaned_comments
    cleanup_empty_posts
    update_counters
    
    puts "Cleanup complete!"
  end
  
  private
  
  def cleanup_orphaned_comments
    puts "Cleaning orphaned comments..."
    Comment.where.missing(:post).destroy_all
  end
  
  def cleanup_empty_posts
    puts "Cleaning empty posts..."
    Post.where.not_exists(:comments).destroy_all
  end
  
  def update_counters
    puts "Updating counters..."
    Post.find_each do |post|
      Post.reset_counters(post.id, :comments)
    end
  end
end
```

## Testing Rake Tasks

```ruby
# spec/tasks/my_app_rake_spec.rb
require "rails_helper"

RSpec.describe "my_app:validate", type: :task do
  include Rake::DSL
  
  before do
    Rake.application.init
    Rake.application.load_rails_tasks
  end
  
  it "validates successfully" do
    expect { Rake::Task["my_app:validate"].invoke }.to output(/valid/).to_stdout
  end
  
  it "handles errors gracefully" do
    allow_any_instance_of(Validator).to receive(:valid?).and_return(false)
    
    expect {
      Rake::Task["my_app:validate"].invoke
    }.to raise_error(SystemExit)
  end
end
```

## File Tasks

```ruby
# lib/tasks/assets.rake
namespace :assets do
  desc "Precompile assets"
  task precompile: :environment do
    puts "Precompiling assets..."
    
    # Use Webpacker or Propshaft
    if defined?(Webpacker)
      Webpacker.compile
    elsif defined?(Propshaft)
      Rails.application.assets.precompile
    end
    
    puts "Assets precompiled!"
  end
  
  desc "Clean old assets"
  task clean: :environment do
    puts "Cleaning old assets..."
    FileUtils.rm_rf(Rails.root.join("public", "assets"))
    puts "Assets cleaned!"
  end
end

# File-based task - only runs if source is newer than target
file "public/assets/manifest.json" => Dir["app/assets/**/*"] do |t|
  Rake::Task["assets:precompile"].invoke
end
```

## Enhanced Rake with Thor

For more complex CLI tools, consider Thor:

```ruby
# lib/tasks/my_app.thor
class MyApp < Thor
  desc "validate [TYPE]", "Validate configuration"
  method_option :verbose, type: :boolean, default: false, aliases: "-v"
  method_option :format, type: :string, default: "text", aliases: "-f"
  
  def validate(type = "full")
    puts "Validating #{type}..." if options[:verbose]
    
    validator = Validator.new(type, format: options[:format])
    result = validator.run
    
    if result.success?
      say "✓ Valid!", :green
    else
      say "✗ Invalid: #{result.errors.join(', ')}", :red
      exit 1
    end
  end
  
  desc "import FILE", "Import data from file"
  method_option :dry_run, type: :boolean, default: false
  
  def import(file)
    puts "Importing #{file}..."
    puts "(Dry run - no changes will be made)" if options[:dry_run]
    
    importer = Importer.new(file, dry_run: options[:dry_run])
    importer.run
  end
end
```

## Best Practices

```ruby
# 1. Always depend on :environment when using Rails models
task :example => :environment do
  User.count  # Safe to use ActiveRecord
end

# 2. Use find_each for large datasets
task :process => :environment do
  User.find_each(batch_size: 1000) do |user|
    # Process user
  end
end

# 3. Provide clear error messages
task :deploy => :environment do
  unless migrations_current?
    puts "ERROR: Pending migrations detected. Run 'rake db:migrate' first."
    exit 1
  end
end

# 4. Use transactions for data integrity
task :import => :environment do
  ActiveRecord::Base.transaction do
    # Import operations
    raise ActiveRecord::Rollback if dry_run?
  end
end

# 5. Support both ENV and args for flexibility
task :export, [:format] => :environment do |t, args|
  format = args[:format] || ENV["EXPORT_FORMAT"] || "json"
  # Export logic
end
```
