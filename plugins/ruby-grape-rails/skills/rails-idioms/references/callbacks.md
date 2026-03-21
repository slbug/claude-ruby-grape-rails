## Callbacks

### The Problem with Active Record Callbacks

```ruby
# ❌ Avoid - Hidden side effects
class Order < ApplicationRecord
  after_create :send_confirmation_email
  after_create :notify_warehouse
  after_create :update_inventory
  after_create :charge_payment
  
  # Testing is hard - callbacks always fire
  # Transaction safety unclear
  # Order of callbacks matters but is implicit
end
```

### Better Callback Patterns

```ruby
# ✅ Good - Boring callbacks for internal state
class Order < ApplicationRecord
  before_validation :generate_order_number, on: :create
  before_save :calculate_total
  
  private
  
  def generate_order_number
    self.order_number ||= "ORD-#{Time.now.to_i}-#{rand(1000..9999)}"
  end
  
  def calculate_total
    self.total = items.sum(&:price)
  end
end

# ✅ Good - External effects in after_commit
class Order < ApplicationRecord
  after_commit :enqueue_notification, on: :create
  
  private
  
  def enqueue_notification
    OrderNotificationJob.perform_later(id)
  end
end

# ✅ Best - Explicit service objects
class OrderCreationService
  def self.call(user:, params:)
    order = nil
    
    Order.transaction do
      order = user.orders.create!(params)
      order.items.create!(params[:items])
      order.calculate_total!
    end
    
    # External effects outside transaction
    OrderNotificationJob.perform_later(order.id)
    InventoryUpdateJob.perform_later(order.id)
    
    order
  end
end
```
