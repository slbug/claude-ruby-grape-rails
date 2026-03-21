# Database-Specific Migration Notes

## PostgreSQL

```ruby
# Use CONCURRENTLY for all indexes on production
class AddIndexConcurrently < ActiveRecord::Migration[7.0]
  disable_ddl_transaction!
  
  def change
    add_index :users, :email, algorithm: :concurrently
  end
end

# Use IF NOT EXISTS for idempotent migrations
def up
  execute <<-SQL
    CREATE INDEX CONCURRENTLY IF NOT EXISTS index_users_on_email 
    ON users (email)
  SQL
end
```

## MySQL

```ruby
# For small tables only
class AddIndexToSmallTable < ActiveRecord::Migration[7.0]
  def change
    add_index :settings, :key  # Only for tables < 100k rows
  end
end
```

For large tables, use pt-online-schema-change outside Rails:

```bash
pt-online-schema-change --alter "ADD INDEX idx_key (key)" \
  D=myapp,t=orders,u=root,p=password
```

## SQLite

```ruby
# SQLite doesn't support concurrent indexes
# But it's typically only used in development/test
class AddIndexToUsers < ActiveRecord::Migration[7.0]
  def change
    add_index :users, :email unless Rails.env.production?
  end
end
```

## Rails 8 Features

```ruby
# Async schema migrations
config.active_record.async_schema_migration = true
```
