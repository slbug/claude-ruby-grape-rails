# Transactions Reference

## ActiveRecord::Base.transaction (Simple cases)

```ruby
ActiveRecord::Base.transaction do
  user = User.create!(params)
  profile = Profile.create!(user: user, default_profile_params)
  user
end
```

## Complex Transactions with rollback

```ruby
result = ActiveRecord::Base.transaction do
  user = User.create(params)
  raise ActiveRecord::Rollback unless user.persisted?
  
  profile = Profile.create(user: user)
  raise ActiveRecord::Rollback unless profile.persisted?
  
  user
end

# result will be nil if transaction rolled back
```

## Upsert Patterns

```ruby
# Insert or update on conflict (PostgreSQL 9.5+)
User.upsert(
  { email: "test@example.com", name: "Test" },
  unique_by: :email,
  returning: %w[id email],
  on_duplicate: :update
)

# Insert or do nothing
User.insert(
  { email: "test@example.com", name: "Test" },
  unique_by: :email,
  on_duplicate: :skip
)

# Bulk upsert
User.upsert_all(
  [
    { email: "a@example.com", name: "A" },
    { email: "b@example.com", name: "B" }
  ],
  unique_by: :email
)
```

## Batch Operations

```ruby
# insert_all (fast bulk insert)
Post.insert_all(posts, returning: %w[id])

# update_all (fast bulk update, skips callbacks)
Post.where(status: :draft).update_all(status: :archived, updated_at: Time.current)

# delete_all (fast bulk delete, skips callbacks)
Post.where("created_at < ?", 1.year.ago).delete_all
```

## Streaming Large Result Sets

```ruby
# For processing large result sets without loading all into memory
# Note: PostgreSQL requires a transaction for server-side cursors
ActiveRecord::Base.transaction do
  Post.find_each(batch_size: 1000) do |post|
    process_post(post)
  end
end

# Alternative for very large tables
Post.in_batches(of: 1000) do |batch|
  batch.each do |post|
    process_post(post)
  end
end
```

## Connection Pool Tuning

```ruby
# config/database.yml
production:
  adapter: postgresql
  pool: <%= ENV.fetch("RAILS_MAX_THREADS") { 5 } %>
  timeout: 5000
  checkout_timeout: 5
  
# Or via config/application.rb
config.active_record.pool = ENV.fetch("RAILS_MAX_THREADS") { 5 }
```

Rule of thumb: `pool_size = (CPU cores * 2) + disk spindles + 1`

## Savepoints (Nested Transactions)

```ruby
ActiveRecord::Base.transaction do
  # Outer transaction
  order = Order.create!(params)
  
  begin
    ActiveRecord::Base.transaction(requires_new: true) do
      # Inner savepoint
      Payment.create!(order: order, amount: order.total)
    end
  rescue ActiveRecord::RecordInvalid => e
    # Inner transaction rolled back, outer continues
    order.update!(status: "payment_failed")
  end
end
```

## Transaction Callbacks

```ruby
class Order < ApplicationRecord
  after_commit :send_confirmation_email, on: :create
  after_commit :update_inventory, on: :update

  # Use after_commit for external effects (jobs, emails, API calls)
  after_commit :schedule_processing, on: :create

  private

  def schedule_processing
    # This runs after successful commit
    OrderProcessingJob.perform_later(id)
  end

  def send_confirmation_email
    # This runs after successful commit
    OrderMailer.confirmation(self).deliver_later
  end
end
```

## Transaction Isolation Levels

```ruby
# PostgreSQL supports: read_uncommitted, read_committed, repeatable_read, serializable
# Default: read_committed

ActiveRecord::Base.transaction(isolation: :serializable) do
  # Highest isolation - prevents phantom reads
  account = Account.lock.find(account_id)
  account.update!(balance: account.balance - amount)
end
```

## Database Locks

```ruby
# Pessimistic locking
Account.transaction do
  account = Account.lock.find(account_id)
  account.update!(balance: account.balance - amount)
end

# Optimistic locking (with lock_version column)
account = Account.find(account_id)
account.update!(balance: account.balance - amount)
# Raises ActiveRecord::StaleObjectError if version changed
```
