## Active Record Patterns

### Scopes

```ruby
class Order < ApplicationRecord
  # Simple scopes
  scope :recent, -> { order(created_at: :desc) }
  scope :pending, -> { where(status: :pending) }
  scope :for_user, ->(user) { where(user: user) }
  
  # Composable scopes
  scope :overdue, -> {
    pending.where('created_at < ?', 3.days.ago)
  }
  
  # Scopes with arguments
  scope :created_between, ->(start_date, end_date) {
    where(created_at: start_date..end_date)
  }
  
  # Avoid complex scopes - use service objects
  # ❌ scope :recommended, -> { ... complex ML logic ... }
end

# Usage
Order.pending.recent.for_user(current_user).limit(10)
```

### Validations

```ruby
class User < ApplicationRecord
  # Presence
  validates :email, :name, presence: true
  
  # Uniqueness
  validates :email, uniqueness: { case_sensitive: false }
  validates :username, uniqueness: true, if: -> { username.present? }
  
  # Format
  validates :email, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :phone, format: { with: /\A\+?[\d\s-]+\z/ }
  
  # Custom validation
  validate :birth_date_in_past
  validate :at_least_18, on: :create
  
  # Conditional validations
  validates :company_name, presence: true, if: :business_account?
  validates :tax_id, presence: true, if: -> { business_account? && us_resident? }
  
  private
  
  def birth_date_in_past
    return unless birth_date.present? && birth_date > Date.today
    errors.add(:birth_date, "must be in the past")
  end
  
  def at_least_18
    return unless birth_date.present? && birth_date > 18.years.ago
    errors.add(:birth_date, "you must be at least 18")
  end
end
```

### Transactions

```ruby
# Basic transaction
ActiveRecord::Base.transaction do
  order = Order.create!(params)
  order.items.create!(item_params)
  Payment.charge!(order.total)
end

# Multi-record transaction
Order.transaction do
  sender = User.lock.find(sender_id)
  receiver = User.lock.find(receiver_id)
  
  sender.debit!(amount)
  receiver.credit!(amount)
  
  Transfer.create!(sender: sender, receiver: receiver, amount: amount)
end

# Transaction with rollback handling
def transfer_funds(from_id, to_id, amount)
  result = nil
  
  ActiveRecord::Base.transaction do
    from_account = Account.lock.find(from_id)
    to_account = Account.find(to_id)
    
    raise InsufficientFunds unless from_account.balance >= amount
    
    from_account.update!(balance: from_account.balance - amount)
    to_account.update!(balance: to_account.balance + amount)
    
    result = Transaction.create!(
      from_account: from_account,
      to_account: to_account,
      amount: amount
    )
  end
  
  result
rescue ActiveRecord::RecordInvalid => e
  Result.failure(e.message)
rescue InsufficientFunds
  Result.failure("Insufficient funds")
end

# Requires_new for nested transactions
def process_order(order)
  Order.transaction do
    order.update!(status: :processing)
    
    # Inner transaction - can rollback without affecting outer
    Order.transaction(requires_new: true) do
      begin
        charge_payment(order)
      rescue PaymentError
        order.update!(status: :payment_failed)
        raise ActiveRecord::Rollback  # Only rolls back inner
      end
    end
    
    order.update!(status: :completed)
  end
end
```
