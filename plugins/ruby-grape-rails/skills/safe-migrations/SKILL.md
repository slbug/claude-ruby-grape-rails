---
name: safe-migrations
description: Safe database migration patterns for Rails. Covers zero-downtime deployments, locking concerns, and backfilling strategies. Use strong_migrations gem or follow manual patterns.
user-invocable: false
paths:
  - db/**
  - "**/db/**"
effort: medium
---
# Safe Migrations

## Scope Check First

This skill is Active Record-first unless the touched package clearly uses Sequel.

Before giving migration advice, identify which migration system owns the file:

- `class ... < ActiveRecord::Migration[...]` → Active Record migration
- `Sequel.migration do` → Sequel migration
- mixed repos may contain both

If the repo is modular or mixed-ORM:

- identify the owning package first
- do not generate Rails migration templates for Sequel packages
- do not assume one global migration strategy for the whole repository

## Iron Laws

1. **Never drop columns/tables while code references them**
2. **Never add column with default on large tables (PG < 11, MySQL)**
3. **Never add index non-concurrently on large tables**
4. **Never change column type on large tables**
5. **Never rename without multi-step process**
6. **Always backfill in batches**

## The Three-Step Deployment Process

```
Deploy 1: Add new structure (nullable, no default)
Deploy 2: Update code; backfill data; switch reads
Deploy 3: Remove old structure; add constraints
```

## Locking Behavior Note

Warnings like "locks table" are generalizations — actual locking behavior varies by database:

| Database | Concurrent Indexes | DDL Transaction Safety | Notes |
|----------|-------------------|------------------------|-------|
| PostgreSQL 11+ | `CONCURRENTLY` supported | `disable_ddl_transaction!` required | Best for zero-downtime |
| PostgreSQL < 11 | `CONCURRENTLY` supported | Same as above | Adding column with default locks table |
| MySQL 8.0+ | No concurrent option | `pt-online-schema-change` for large tables | InnoDB has different locking model |
| MySQL 5.7 | No concurrent option | Use percona toolkit | More locking on DDL |
| SQLite | N/A (file-based) | Locks entire database | Development/test only |

Always consult your database documentation for exact locking behavior. See `references/database-specific.md` for detailed guidance.

## Safe Patterns

### Adding a Column

**Unsafe:** `add_column :users, :active, :boolean, default: true, null: false`

**Safe:**

```ruby
# Migration 1: Add nullable (idempotent for safety)
class AddActiveToUsers < ActiveRecord::Migration[8.1]
  def change
    add_column :users, :active, :boolean unless column_exists?(:users, :active)
  end
end

# Model: Set default in callback
before_create { self.active = true if active.nil? }

# Migration 2 (after Deploy 2): Backfill, add constraints
class BackfillActiveOnUsers < ActiveRecord::Migration[8.1]
  disable_ddl_transaction!
  
  def up
    User.unscoped.in_batches { |b| b.update_all(active: true); sleep(0.1) }
    change_column_null :users, :active, false
  end
end
```

### Adding an Index

**Unsafe:** `add_index :orders, :user_id` (locks table)

**Safe:**

```ruby
class AddIndexToOrders < ActiveRecord::Migration[8.1]
  disable_ddl_transaction!
  
  def change
    add_index :orders, :user_id, algorithm: :concurrently, if_not_exists: true
  end
end
```

### Removing a Column

**Unsafe:** Direct `remove_column` while code uses it

**Safe:**

```ruby
# Deploy 1: Remove all references from code
# Deploy 2: Add to ignored_columns
self.ignored_columns = [:old_field]
# Deploy 3: Drop column (idempotent check)
class RemoveOldFieldFromUsers < ActiveRecord::Migration[8.1]
  def change
    remove_column :users, :old_field, if_exists: true
  end
end
```

### Renaming a Column

**Unsafe:** `rename_column :users, :name, :full_name`

**Safe:**

```ruby
# Migration 1: Add new column (idempotent)
class AddFullNameToUsers < ActiveRecord::Migration[8.1]
  def change
    add_column :users, :full_name, :string unless column_exists?(:users, :full_name)
  end
end

# Model: Dual-write accessors
def name
  read_attribute(:name) || full_name
end
def name=(v)
  write_attribute(:name, v)
  self.full_name = v
end

# Deploy 2: Backfill
User.where(full_name: nil).in_batches { |b| b.update_all('full_name = name'); sleep(0.1) }

# Migration 2 (Deploy 3): Remove old (idempotent)
class RemoveNameFromUsers < ActiveRecord::Migration[8.1]
  def change
    remove_column :users, :name, if_exists: true
  end
end
```

### Changing Column Type

**Unsafe:** `change_column :products, :price, :decimal`

**Safe:**

```ruby
# Migration 1: Add new column (idempotent)
class AddPriceDecimalToProducts < ActiveRecord::Migration[8.1]
  def change
    unless column_exists?(:products, :price_decimal)
      add_column :products, :price_decimal, :decimal, precision: 10, scale: 2
    end
  end
end

# Model: Read from new, sync on save
def price
  price_decimal || read_attribute(:price)
end
before_save { self.price_decimal ||= read_attribute(:price) }

# Deploy 2: Backfill
Product.where(price_decimal: nil).find_each { |p| p.update_column(:price_decimal, p.read_attribute(:price)) }

# Migration 2 (Deploy 3): Remove old, rename (both idempotent)
class RemovePriceFromProducts < ActiveRecord::Migration[8.1]
  def up
    remove_column :products, :price, if_exists: true
    rename_column :products, :price_decimal, :price if column_exists?(:products, :price_decimal)
  end
end
```

### Adding a Foreign Key

**Unsafe:** `add_foreign_key :orders, :users` (locks both tables)

**Safe:**

```ruby
class AddForeignKeyToOrders < ActiveRecord::Migration[8.1]
  def up
    # Add FK without validating (brief lock)
    add_foreign_key :orders, :users, validate: false, if_not_exists: true
    
    # Validate in separate step (can be separate migration)
    execute 'ALTER TABLE orders VALIDATE CONSTRAINT fk_orders_users' 
  end
  
  def down
    remove_foreign_key :orders, :users, if_exists: true
  end
end
```

### Backfilling Data

**Unsafe:** `User.update_all(status: 'active')` on large tables

**Safe:**

```ruby
class BackfillUserStatus < ActiveRecord::Migration[8.1]
  disable_ddl_transaction!
  
  def up
    User.unscoped.where(status: nil).in_batches(of: 1000) do |batch|
      batch.update_all(status: 'active')
      sleep(0.1)
    end
  end
end
```

**For very large tables:** Use background jobs (see references/backfill-patterns.md)

## Database-Specific Notes

**PostgreSQL:** Use `CONCURRENTLY` for all indexes. Use `IF NOT EXISTS` for idempotent migrations.

**MySQL:** No concurrent indexes. Use `pt-online-schema-change` for large tables.

**SQLite:** Development/test only. No concurrent support needed.

## Sequel Note

For Sequel packages, apply the same zero-downtime principles but use Sequel
migration syntax and package-local data access patterns. Avoid dropping raw
Active Record migration classes into a Sequel package just because the
top-level repo also contains Rails.

## Migration Checklist

Before committing:

- [ ] Will this lock tables? → Use `disable_ddl_transaction!` + `algorithm: :concurrently`
- [ ] Adding column with default on large table? → Use three-step approach
- [ ] Renaming something? → Use three-step rename
- [ ] Changing column type? → Use add-new-column approach
- [ ] Removing a column? → First ignore in model
- [ ] Backfilling data? → Use batching with throttling
- [ ] Is this reversible? → Define `up`/`down` if not

## Anti-patterns

**Don't:** Use raw SQL without escaping (SQL injection risk)  
**Don't:** Use model classes in migrations (model may change)  
**Don't:** Forget error handling in batch operations  
**Don't:** Rollback production migrations (fix forward instead)

## References

- `references/backfill-patterns.md` — Background job backfilling strategies
- `references/strong-migrations-setup.md` — Gem configuration details
- `references/database-specific.md` — PG, MySQL, SQLite specifics
- `references/emergency-procedures.md` — Canceling stuck migrations
