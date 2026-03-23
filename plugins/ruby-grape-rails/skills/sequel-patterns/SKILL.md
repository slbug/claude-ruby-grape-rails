---
name: sequel-patterns
description: Sequel ORM patterns for high-performance Ruby/Rails applications. Covers datasets, migrations, associations, and when to choose Sequel over ActiveRecord.
user-invocable: false
effort: medium
---
# Sequel Patterns

Sequel is a flexible, high-performance ORM for Ruby.

## When to Choose Sequel

| Factor | ActiveRecord | Sequel |
|--------|--------------|--------|
| **Performance** | Good | 6-7x faster simple queries |
| **Memory** | ~100MB | ~35MB for same dataset |
| **Flexibility** | Convention-based | Explicit control |
| **Learning Curve** | Gentle | Moderate |
| **Rails Integration** | Native | Via `sequel-rails` gem |
| **Complex SQL** | Limited | Excellent |

Use **Sequel** when:

- High-throughput read operations
- Memory-constrained environments
- Complex SQL requirements
- Non-Rails applications
- Data processing pipelines

Use **ActiveRecord** when:

- Standard Rails application
- Team familiar with Rails conventions
- Rapid prototyping
- Heavy use of Rails generators

## Installation

### Standalone

```ruby
# Gemfile
gem 'sequel'
gem 'pg'  # or 'mysql2', 'sqlite3'

# Connect
DB = Sequel.connect('postgres://user:pass@localhost/mydb')
```

### With Rails

```ruby
# Gemfile
gem 'sequel'
gem 'sequel-rails'

# Initialize
# config/initializers/sequel.rb
DB = Sequel.connect(Rails.configuration.database_configuration[Rails.env])
```

## Models

### Defining Models

```ruby
class User < Sequel::Model
  # Table name inferred: :users
  
  # Explicit table name
  set_dataset :my_users
end

# Alternative: dataset block
class User < Sequel::Model
  dataset do
    where(active: true)
  end
end
```

### Schema Definition

```ruby
# migrations/001_create_users.rb
Sequel.migration do
  change do
    create_table :users do
      primary_key :id
      String :name, null: false
      String :email, null: false, unique: true
      DateTime :created_at, null: false, default: Sequel::CURRENT_TIMESTAMP
      
      index :email
    end
  end
end
```

## Datasets

The core of Sequel's power is the Dataset abstraction.

### Basic Queries

```ruby
# Retrieving
users = User.all                          # Array of User objects
user = User.first                         # First user
user = User[id: 1]                        # By primary key
user = User.find(name: 'John')            # By conditions

# Filtering
active_users = User.where(active: true)
recent = User.where(created_at: > 1.week.ago)

# Chaining
dataset = User.where(active: true)
              .where(created_at: > 1.month.ago)
              .order(:created_at)
              .limit(10)
```

### Advanced Filtering

```ruby
# Complex conditions
User.where(Sequel.like(:name, 'J%'))
User.where(Sequel.ilike(:email, '%@gmail.com'))
User.where(id: 1..100)

# Boolean logic
User.where(Sequel.or(active: true, admin: true))
User.where(Sequel.~{active: false})  # NOT

# Raw SQL (escape carefully!)
User.where(Sequel.lit('created_at > ?', 1.week.ago))
```

### Dataset Operations

```ruby
# Map/Select specific columns
User.select(:id, :name)
User.select(Sequel.lit('name AS full_name'))

# Aggregations
count = User.count
max_id = User.max(:id)
avg_age = User.avg(:age)

# Grouping
User.group(:role).select(:role, Sequel.count(:id).as(:count))

# Window functions
User.select_append { row_number.function.over(order: :created_at) }
```

## Associations

### Defining Associations

```ruby
class User < Sequel::Model
  one_to_many :posts
  one_to_one :profile
  many_to_many :roles
  many_to_one :company
end

class Post < Sequel::Model
  many_to_one :user
end
```

### Eager Loading

```ruby
# Prevents N+1
users = User.eager(:posts).all
users.each do |user|
  user.posts.each { |post| puts post.title }
end

# Multiple associations
User.eager(:posts, :profile, :company)

# Nested eager loading
User.eager(posts: :comments)

# Custom eager loading
dataset = User.eager_graph(:posts)
# Generates JOIN, access via user.posts
```

### Association Options

```ruby
class User < Sequel::Model
  one_to_many :posts, 
    class: :Post,
    key: :author_id,
    conditions: { published: true },
    order: :created_at,
    limit: 10
  
  many_to_many :roles,
    join_table: :user_roles,
    left_key: :user_id,
    right_key: :role_id
end
```

## Transactions

```ruby
# Basic transaction
DB.transaction do
  user = User.create(name: 'John')
  Post.create(user_id: user.id, title: 'Hello')
end

# Savepoints
DB.transaction do
  User.create(name: 'John')
  
  DB.transaction(savepoint: true) do
    User.create(name: 'Jane')
    raise Sequel::Rollback  # Only rolls back inner transaction
  end
  
  # John is saved, Jane is not
end

# Transaction options
DB.transaction(
  isolation: :serializable,
  retry_on: [Sequel::DatabaseDisconnectError],
  num_retries: 3
) do
  # Work here
end
```

## Sidekiq and Commit Hooks

If Sidekiq is present in a Sequel package, do not blindly apply Active Record callback advice.

Prefer transaction-aware enqueueing:

```ruby
DB.transaction do
  payment = Payment.create(amount_cents: 1000)
  DB.after_commit { ChargeCustomerJob.perform_async(payment.id) }
end
```

Model hooks exist too:

```ruby
class Payment < Sequel::Model
  def after_commit
    super
    ChargeCustomerJob.perform_async(id)
  end
end
```

In mixed Active Record + Sequel repos:

- identify the package/ORM before applying callback guidance
- do not recommend `after_commit` on `ApplicationRecord` when the touched model is `Sequel::Model`
- do not assume the migration framework is Rails just because the repo contains Rails

## Validations

```ruby
class User < Sequel::Model
  plugin :validation_helpers
  
  def validate
    super
    validates_presence [:name, :email]
    validates_unique :email
    validates_format /\A[\w+\-.]+@[a-z\d\-]+(\.[a-z\d\-]+)*\.[a-z]+\z/i, :email
    validates_length_range 3..50, :name
  end
end
```

### Validation Plugins

```ruby
# Auto-validations based on schema
plugin :auto_validations

# Email validation
plugin :validation_helpers
validates_email :email

# Password hashing
plugin :secure_password
```

## Plugins

### Essential Plugins

```ruby
# Timestamps (created_at, updated_at)
plugin :timestamps

# Pagination
plugin :pagination
User.dataset.paginate(2, 20)  # Page 2, 20 per page

# Caching
plugin :caching, cache: Redis.new

# JSON serialization
plugin :json_serializer
user.to_json

# Serialization for specific columns
plugin :serialization, :json, :preferences
```

### Advanced Plugins

```ruby
# Polymorphism
plugin :class_table_inheritance, key: :type

# Versioning/auditing
plugin :audited

# Soft delete
plugin :soft_delete
User.first.delete  # Sets deleted_at, doesn't remove

# Tree structures
plugin :rcte_tree  # Recursive CTE for hierarchies
```

## Performance Patterns

### Connection Pooling

```ruby
DB = Sequel.connect(
  'postgres://user:pass@localhost/mydb',
  max_connections: 10,
  pool_timeout: 30,
  connect_timeout: 10,
  read_timeout: 30
)
```

### Query Optimization

```ruby
# Use only what you need
User.select(:id, :name).all  # Faster than SELECT *

# Return raw hashes (no model instantiation)
User.to_hash(:id, :name)  # { 1 => 'John', 2 => 'Jane' }

# Stream large datasets
User.each_row { |row| process(row) }

# Batch processing
User.dataset.each_chunk(1000) do |users|
  users.each { |u| process(u) }
end
```

### Prepared Statements

```ruby
# Prepare once, execute many
statement = DB[:users].where(id: :$id).prepare(:first, :select_user)

statement.call(id: 1)
statement.call(id: 2)
```

## Migrations

### Migration Structure

```ruby
# migrations/001_create_users.rb
Sequel.migration do
  up do
    create_table :users do
      primary_key :id
      String :name, null: false
      DateTime :created_at
    end
  end
  
  down do
    drop_table :users
  end
end
```

### Migration Helpers

```ruby
Sequel.migration do
  change do
    # Add column
    add_column :users, :age, Integer, default: 0
    
    # Add index
    add_index :users, :email, unique: true
    
    # Change column
    set_column_type :users, :age, :bigint
    
    # Rename
    rename_column :users, :name, :full_name
    
    # Foreign key
    alter_table :posts do
      add_foreign_key :user_id, :users
    end
  end
end
```

## Iron Laws

1. **Use datasets for complex queries** - More efficient than AR scopes
2. **Eager load associations** - Always prevent N+1
3. **Use transactions for multi-step** - Ensure data integrity
4. **Prepare statements for repeated queries** - Performance boost
5. **Stream large datasets** - Don't load everything into memory
6. **Validate at the model** - Database + application validation
7. **Use appropriate connection pool size** - Match your workload

## Comparison with ActiveRecord

### Common Operations

| Operation | ActiveRecord | Sequel |
|-----------|--------------|--------|
| Find by ID | `User.find(1)` | `User[1]` |
| Find first | `User.first` | `User.first` |
| Where | `User.where(active: true)` | `User.where(active: true)` |
| Order | `User.order(:name)` | `User.order(:name)` |
| Limit | `User.limit(10)` | `User.limit(10)` |
| Create | `User.create(name: 'John')` | `User.create(name: 'John')` |
| Update | `user.update(name: 'Jane')` | `user.update(name: 'Jane')` |
| Destroy | `user.destroy` | `user.delete` |
| Eager load | `User.includes(:posts)` | `User.eager(:posts)` |
| Join | `User.joins(:posts)` | `User.join(:posts)` |

### Key Differences

```ruby
# ActiveRecord: Query executes immediately
users = User.where(active: true)  # Query runs
users.each { |u| puts u.name }

# Sequel: Query is lazy, executes on enumeration
users = User.where(active: true)  # No query yet
users.each { |u| puts u.name }    # Query runs here

# Sequel: Explicit .all to execute
dataset = User.where(active: true)
users = dataset.all               # Execute and return array
```

### Complex Queries

```ruby
# ActiveRecord - limited
User.where('created_at > ?', 1.week.ago)
  .group(:role)
  .having('COUNT(*) > 5')

# Sequel - full control
User.where(created_at: > 1.week.ago)
  .group(:role)
  .having(Sequel.count(:id) > 5)
  .select(:role, Sequel.count(:id).as(:count))
```

## Testing

```ruby
# spec/user_spec.rb
describe User do
  before do
    DB[:users].delete
  end
  
  it "creates a user" do
    user = User.create(name: 'John', email: 'john@example.com')
    expect(user.id).not_to be_nil
  end
  
  it "validates presence" do
    user = User.new
    expect(user.valid?).to be false
    expect(user.errors[:name]).to include('is not present')
  end
end
```

### Test Database Setup

```ruby
# spec_helper.rb
DB = Sequel.connect('postgres://localhost/myapp_test')

RSpec.configure do |config|
  config.around(:each) do |example|
    DB.transaction(rollback: :always) do
      example.run
    end
  end
end
```
