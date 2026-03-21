# Strong Migrations Gem Setup

## Installation

```ruby
# Gemfile
gem 'strong_migrations'
```

```bash
bundle install
rails generate strong_migrations:install
```

## Configuration

```ruby
# config/initializers/strong_migrations.rb
StrongMigrations.enabled = true

# Target PostgreSQL version
StrongMigrations.target_version = 14

# Start checking after this migration
StrongMigrations.start_after = 20240101000000

# Disable safe-by-default (manual control)
StrongMigrations.safe_by_default = false
```

## What It Blocks

The gem automatically blocks:

- Adding columns with default values (on PG < 11, MySQL)
- Adding non-concurrent indexes
- Adding foreign keys without `validate: false`
- Changing column types
- Removing columns (without first ignoring)
- Renaming columns/tables

## Bypassing Checks

For intentional unsafe operations:

```ruby
class IntentionallyUnsafeMigration < ActiveRecord::Migration[7.0]
  def change
    StrongMigrations.enabled = false
    # ... unsafe operation ...
  ensure
    StrongMigrations.enabled = true
  end
end
```
