# Emergency Migration Procedures

## Canceling a Running Migration

| Goal | Command |
|---|---|
| Find the migration process | `ps aux \| grep migrate` |
| Kill it (last resort) | `kill -9 <pid>` |
| Check migration status | `rails db:migrate:status` |
| If stuck, manually drop the row | `rails dbconsole` then `DELETE FROM schema_migrations WHERE version = '20240101120000';` |

## Rolling Back Production

**Never rollback on production without extreme caution!** Instead, fix forward with new migrations.

If absolutely necessary, roll back one step or a specific
migration:

```bash
RAILS_ENV=production rails db:rollback STEP=1
RAILS_ENV=production rails db:migrate:down VERSION=20240101120000
```

## Testing Migrations

```ruby
# test/migrations/add_active_to_users_test.rb
require 'test_helper'

class AddActiveToUsersTest < ActiveSupport::TestCase
  self.use_transactional_tests = false
  
  setup do
    @connection = ActiveRecord::Base.connection
    @migration = AddActiveToUsers.new
  end
  
  test "adds active column" do
    @migration.migrate(:up)
    assert @connection.column_exists?(:users, :active)
  ensure
    @migration.migrate(:down)
  end
  
  test "is reversible" do
    @migration.migrate(:up)
    @migration.migrate(:down)
    assert_not @connection.column_exists?(:users, :active)
  end
end
```

## Common Migration Patterns

### Creating a Join Table

```ruby
class CreateCategoriesProducts < ActiveRecord::Migration[8.1]
  def change
    create_table :categories_products, id: false, if_not_exists: true do |t|
      t.belongs_to :category, null: false, foreign_key: true
      t.belongs_to :product, null: false, foreign_key: true
      t.timestamps
    end
    
    add_index :categories_products, [:category_id, :product_id], 
              unique: true, algorithm: :concurrently, if_not_exists: true
    add_index :categories_products, :product_id, algorithm: :concurrently, if_not_exists: true
  end
end
```

### Adding JSONB Column

```ruby
class AddMetadataToProducts < ActiveRecord::Migration[7.0]
  def change
    add_column :products, :metadata, :jsonb, default: {}
    add_index :products, :metadata, using: :gin, algorithm: :concurrently
  end
end
```

### Adding Enum Column

```ruby
class AddStatusToOrders < ActiveRecord::Migration[7.0]
  def up
    create_enum :order_status, %w[pending paid shipped cancelled]
    add_column :orders, :status, :enum, enum_type: :order_status, 
               default: 'pending', null: false
  end
  
  def down
    remove_column :orders, :status
    execute 'DROP TYPE order_status'
  end
end
```
