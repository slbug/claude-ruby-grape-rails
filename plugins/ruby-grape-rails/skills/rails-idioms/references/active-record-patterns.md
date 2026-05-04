## Active Record Patterns

### Scopes

```ruby
class Order < ApplicationRecord
  scope :recent,        -> { order(created_at: :desc) }
  scope :pending,       -> { where(status: :pending) }
  scope :for_user,      ->(user) { where(user: user) }
  scope :overdue,       -> { pending.where('created_at < ?', 3.days.ago) }
  scope :created_between, ->(start_date, end_date) {
    where(created_at: start_date..end_date)
  }
end

Order.pending.recent.for_user(current_user).limit(10)
```

Reject scopes that embed business / ML logic. Move that to a service
object or query class — scopes stay declarative SQL building blocks.

### Validations

| Form | Use |
|---|---|
| `presence: true` | Required column |
| `uniqueness: { case_sensitive: false }` | Case-insensitive uniqueness |
| `format: { with: regex }` | Format rule |
| `validate :method` | Custom validation method |
| `if:` / `unless:` (symbol or lambda) | Conditional |
| `on: :create` / `on: :update` | Lifecycle-scoped |

```ruby
class User < ApplicationRecord
  validates :email, :name, presence: true
  validates :email, uniqueness: { case_sensitive: false }
  validates :username, uniqueness: true, if: -> { username.present? }
  validates :email, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :phone, format: { with: /\A\+?[\d\s-]+\z/ }

  validate :birth_date_in_past
  validate :at_least_18, on: :create

  validates :company_name, presence: true, if: :business_account?
  validates :tax_id,       presence: true, if: -> { business_account? && us_resident? }

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

Iron Law 5: wrap multi-step operations in
`ActiveRecord::Base.transaction`.

Single transaction:

```ruby
ActiveRecord::Base.transaction do
  order = Order.create!(params)
  order.items.create!(item_params)
  Payment.charge!(order.total)
end
```

Pessimistic locking on both sides of a balance transfer:

```ruby
Order.transaction do
  sender   = User.lock.find(sender_id)
  receiver = User.lock.find(receiver_id)

  sender.debit!(amount)
  receiver.credit!(amount)

  Transfer.create!(sender: sender, receiver: receiver, amount: amount)
end
```

Result-object wrapper around a transaction:

```ruby
def transfer_funds(from_id, to_id, amount)
  result = nil

  ActiveRecord::Base.transaction do
    from_account = Account.lock.find(from_id)
    to_account   = Account.find(to_id)

    raise InsufficientFunds unless from_account.balance >= amount

    from_account.update!(balance: from_account.balance - amount)
    to_account.update!(balance: to_account.balance + amount)

    result = Transaction.create!(
      from_account: from_account,
      to_account:   to_account,
      amount:       amount
    )
  end

  result
rescue ActiveRecord::RecordInvalid => e
  Result.failure(e.message)
rescue InsufficientFunds
  Result.failure("Insufficient funds")
end
```

Nested savepoint via `requires_new: true`. Inner rollback (raised
`ActiveRecord::Rollback`) leaves outer transaction intact:

```ruby
def process_order(order)
  Order.transaction do
    order.update!(status: :processing)

    Order.transaction(requires_new: true) do
      charge_payment(order)
    rescue PaymentError
      order.update!(status: :payment_failed)
      raise ActiveRecord::Rollback
    end

    order.update!(status: :completed)
  end
end
```
