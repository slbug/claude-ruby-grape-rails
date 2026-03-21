# Migrations Reference

## Basic Migration

```ruby
class CreateUsers < ActiveRecord::Migration[7.1]
  def change
    create_table :users, id: :uuid do |t|
      t.string :email, null: false
      t.string :name
      t.string :role, default: "user"
      t.string :password_digest

      t.timestamps
    end

    add_index :users, :email, unique: true
  end
end
```

## Add Foreign Key (Safe - 2 steps)

```ruby
# Step 1: Add without validation (fast, no table lock)
class AddUserToPosts < ActiveRecord::Migration[7.1]
  def change
    add_reference :posts, :user, null: false, foreign_key: { validate: false }
    add_index :posts, :user_id
  end
end

# Step 2: Validate in separate migration (separate deploy)
class ValidatePostsUserFk < ActiveRecord::Migration[7.1]
  def up
    execute "ALTER TABLE posts VALIDATE CONSTRAINT posts_user_id_fkey"
  end
  
  def down
    # No-op - validation cannot be undone
  end
end
```

## Add NOT NULL (Safe - 3 steps)

```ruby
# Step 1: Add check constraint without validation
class AddActiveConstraint < ActiveRecord::Migration[7.1]
  def change
    add_check_constraint :products, "active IS NOT NULL", name: "active_not_null", validate: false
  end
end

# Step 2: Backfill data (separate deploy)
class BackfillActiveDefault < ActiveRecord::Migration[7.1]
  def up
    Product.where(active: nil).update_all(active: false)
  end
  
  def down
    # No-op
  end
end

# Step 3: Validate constraint, add NOT NULL, drop constraint
class MakeActiveNotNull < ActiveRecord::Migration[7.1]
  def up
    execute "ALTER TABLE products VALIDATE CONSTRAINT active_not_null"
    change_column_null :products, :active, false, false
    remove_check_constraint :products, name: "active_not_null"
  end
  
  def down
    change_column_null :products, :active, true
  end
end
```

## Concurrent Index (Large Tables)

```ruby
class AddSlugIndexToPosts < ActiveRecord::Migration[7.1]
  disable_ddl_transaction!

  def change
    add_index :posts, :slug, algorithm: :concurrently
  end
end
```

## Batched Data Migration

```ruby
class MigrateUserStatus < ActiveRecord::Migration[7.1]
  def up
    User.where(status: nil).find_each do |user|
      user.update_column(:status, calculate_status(user))
    end
  end
  
  def down
    # No-op
  end
  
  private
  
  def calculate_status(user)
    # Migration logic here
    "active"
  end
end
```

## Mixed Primary Key Types (bigint + uuid)

When integrating with gems that use UUID PKs while your project uses bigint:

```ruby
# RIGHT: Explicit type ONLY on specific associations
class Interview < ApplicationRecord
  belongs_to :user                          # bigint (default)
  belongs_to :conversation, optional: true   # bigint (default)
  
  # For UUID associations, specify the type
  # belongs_to :legacy_record, type: :uuid
end
```

In migrations, match the referenced table's PK type:

```ruby
change_table :interviews do |t|
  t.references :user, null: false, type: :bigint, foreign_key: true
  t.references :legacy_record, type: :uuid, foreign_key: true
end
```

## Associations

```ruby
class User < ApplicationRecord
  # One-to-many (always specify dependent!)
  has_many :posts, dependent: :destroy
  has_many :comments, dependent: :nullify
  
  # Many-to-many
  has_and_belongs_to_many :tags
  # Or with join model:
  has_many :post_tags
  has_many :tags, through: :post_tags
end

class Post < ApplicationRecord
  belongs_to :user
  belongs_to :category, optional: true
  
  # Self-referential
  belongs_to :parent, class_name: "Post", optional: true
  has_many :children, class_name: "Post", foreign_key: :parent_id, dependent: :destroy
  
  # Has one through
  has_one :organization, through: :user
end
```

## Optimistic Locking

```ruby
class Product < ApplicationRecord
  # Rails provides optimistic locking with lock_version
  # No special schema needed - just add the column
end

# Migration
add_column :products, :lock_version, :integer, default: 0, null: false

# Usage - raises ActiveRecord::StaleObjectError if version changed
product.update!(name: "New Name")
```

## Migration Safety Checklist

- [ ] Use `disable_ddl_transaction!` with `algorithm: :concurrently` for indexes
- [ ] Add foreign keys with `validate: false` first, validate separately
- [ ] Add NOT NULL constraints in 3 steps (check constraint → backfill → validate)
- [ ] For large tables, process data in batches with `find_each`
- [ ] Test migrations on production-like data volumes
- [ ] Always provide `down` methods or use `reversible` blocks
