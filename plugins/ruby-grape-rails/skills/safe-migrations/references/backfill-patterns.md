# Backfill Patterns for Large Tables

## Background Job Backfilling

For very large tables, use background jobs to avoid long-running migrations:

```ruby
# Migration (idempotent)
class AddStatusToUsers < ActiveRecord::Migration[8.1]
  def change
    add_column :users, :status, :string unless column_exists?(:users, :status)
    add_index :users, :status, where: "status IS NULL", algorithm: :concurrently, if_not_exists: true
  end
end

# Background job
class BackfillUserStatusJob < ApplicationJob
  BATCH_SIZE = 1000
  
  def perform(batch_number = 0)
    batch = User.where(status: nil).limit(BATCH_SIZE)
    
    if batch.any?
      batch.update_all(status: 'active')
      BackfillUserStatusJob.perform_later(batch_number + 1)
    end
  end
end

# Rake task to kick off
namespace :backfill do
  task user_status: :environment do
    BackfillUserStatusJob.perform_later
  end
end
```

## Adding a NOT NULL Constraint

Three-step approach for PostgreSQL:

```ruby
# Migration 1: Add check constraint as NOT NULL alternative (idempotent)
class AddActiveCheckToUsers < ActiveRecord::Migration[8.1]
  def up
    return if check_constraint_exists?(:users, "users_active_not_null")
    add_check_constraint :users, "active IS NOT NULL", 
                         name: "users_active_not_null", 
                         validate: false
  end
end

# Backfill nil values first
namespace :backfill do
  task users_active: :environment do
    User.where(active: nil).in_batches.update_all(active: true)
  end
end

# Migration 2: Validate constraint
class ValidateActiveCheckOnUsers < ActiveRecord::Migration[8.1]
  def up
    execute 'ALTER TABLE users VALIDATE CONSTRAINT users_active_not_null'
  end
end

# Migration 3: Make it proper NOT NULL (PostgreSQL 12+)
class ChangeActiveToNotNull < ActiveRecord::Migration[8.1]
  def up
    remove_check_constraint :users, name: "users_active_not_null"
    change_column_null :users, :active, false
  end
end
```

## Error Handling in Batches

Handle individual record failures:

```ruby
default_value = calculate_default
User.where(some_attr: nil).find_each do |user|
  begin
    user.update!(some_attr: default_value)
  rescue => e
    Rails.logger.error "Failed to update user #{user.id}: #{e.message}"
  end
end
```

## Temporary Models in Migrations

Don't use production model classes in migrations:

```ruby
# ❌ Bad
class BackfillData < ActiveRecord::Migration[8.1]
  def up
    User.update_all(active: true)  # Model may change!
  end
end

# ✅ Good
class BackfillData < ActiveRecord::Migration[8.1]
  class MigrationUser < ActiveRecord::Base
    self.table_name = 'users'
  end
  
  def up
    MigrationUser.update_all(active: true)
  end
end
```
