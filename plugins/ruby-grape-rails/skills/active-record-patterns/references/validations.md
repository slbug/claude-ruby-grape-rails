# Active Record Validations and Attributes

Active Record provides a robust validation system that ensures data integrity before
records are saved to the database. Validations run automatically on create and update
operations, with support for conditional logic, custom validators, and multiple validation contexts.

## Validations vs Direct Assignment

| Method | Use When |
|--------|----------|
| `validates` | External data (user input, API) |
| Direct assignment | Internal trusted data (timestamps, computed) |
| `assign_attributes` | Internal data with mass assignment |
| `update_column` | Skip callbacks/validations (use sparingly) |

```ruby
# External data - use validations
class User < ApplicationRecord
  validates :email, presence: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :password, presence: true, length: { minimum: 12, maximum: 72 }
  
  def registration_validation
    valid?
    errors.add(:email, :invalid) unless email_valid?
    errors.empty?
  end
end

# Internal data - direct assignment
private

def hash_password
  return unless password.present?
  self.password_digest = BCrypt::Password.create(password)
end
```

## Multiple Validation Contexts

```ruby
class User < ApplicationRecord
  # Different validations for different operations
  validates :email, :password, :name, presence: true, on: :create
  validates :email, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :password, length: { in: 12..72 }, on: :create
  
  # Profile update - different context
  validates :bio, length: { maximum: 500 }, on: :profile_update
  validates :name, presence: true, on: :profile_update
end

# Usage
user.save(context: :profile_update)
user.update(params, context: :password_change)
```

## Custom Validations

```ruby
class Order < ApplicationRecord
  validates :quantity, :unit_price, presence: true
  validate :positive_total

  private

  def positive_total
    return unless quantity.present? && unit_price.present?
    
    if quantity * unit_price < 0
      errors.add(:quantity, "total must be positive")
    end
  end
end
```

## Transaction-Safe Operations

```ruby
class Post < ApplicationRecord
  after_save :update_author_count, if: :saved_change_to_published_at?

  private

  def update_author_count
    # Runs inside the transaction
    author.increment!(:post_count) if published_at.present?
  end
end
```

## JSON/JSONB Attributes (Rails 7.1+)

**Use `store_accessor` or `attribute` when:**

- Never query child independently
- Never share child across parents
- Always loaded with parent (single query)

```ruby
# JSONB attributes (stored as JSONB)
class User < ApplicationRecord
  # Store settings as JSONB
  store_accessor :settings, :dark_mode, :timezone, :language
  
  # Or use attribute with type
  attribute :preferences, :json, default: {}
end

# Migration
class AddSettingsToUsers < ActiveRecord::Migration[7.1]
  def change
    add_column :users, :settings, :jsonb, default: {}
    add_column :users, :preferences, :jsonb, default: {}
    
    add_index :users, :settings, using: :gin
  end
end
```

## Field Types

| Need | Rails Type | PostgreSQL | Notes |
|------|-----------|------------|-------|
| Primary key | `:bigint` / `:uuid` | `bigint` / `uuid` | Prefer UUIDs for distributed systems |
| Text | `:string` | `varchar` | Default 255 chars |
| Long text | `:text` | `text` | No limit |
| Integer | `:integer` | `integer` | |
| Money | `:integer` | `integer` | Store cents (never float!) |
| Decimal | `:decimal` | `numeric` | Precise calculations |
| Boolean | `:boolean` | `boolean` | |
| Date | `:date` | `date` | |
| DateTime | `:datetime` | `timestamptz` | With timezone |
| JSON | `:json` / `:jsonb` | `jsonb` | Use jsonb for PostgreSQL |
| Enum | `enum` | `integer` / `varchar` | Type-safe |
| Array | `:array` | `varchar[]` | PostgreSQL arrays |

## Enum Definition

```ruby
class User < ApplicationRecord
  enum role: {
    user: 0,
    moderator: 1,
    admin: 2
  }
end
```
