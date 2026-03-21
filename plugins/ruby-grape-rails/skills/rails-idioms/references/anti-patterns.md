## Anti-patterns

```ruby
# ❌ Don't use callbacks for external side effects
class Order < ApplicationRecord
  after_create :send_email  # Hard to test, hard to reason about
end

# ✅ Use explicit service objects
OrderCreator.new(user).create(params)  # Returns order, enqueues email job

# ❌ Don't put business logic in controllers
class OrdersController < ApplicationController
  def create
    order = Order.new(params)
    if order.save
      order.items.each do |item|
        Inventory.decrement(item.product_id, item.quantity)
      end
      PaymentGateway.charge(order.total)
      OrderMailer.confirmation(order).deliver_later
      redirect_to order
    end
  end
end

# ✅ Delegate to service objects
class OrdersController < ApplicationController
  def create
    result = OrderCreator.call(user: current_user, params: order_params)
    
    if result.success?
      redirect_to result.order
    else
      render :new, status: :unprocessable_entity
    end
  end
end

# ❌ Don't use raw SQL when AR can handle it
User.find_by_sql("SELECT * FROM users WHERE active = true")

# ✅ Use AR where possible
User.where(active: true)

# ❌ Don't load associations in loops
orders.each { |o| o.user.name }  # N+1 query

# ✅ Eager load
orders.includes(:user).each { |o| o.user.name }

# ❌ Don't use select * in APIs
render json: User.all  # Returns all fields including sensitive data

# ✅ Use serializers or explicit fields
render json: users.as_json(only: %i[id name email])
# Or use Active Model Serializers / Alba / etc.
```
