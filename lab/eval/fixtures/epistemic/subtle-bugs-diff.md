# Diff Review — Subtle Issues

Review this diff for correctness, security, and performance. List every
issue you find with severity.

```ruby
# app/services/orders/mark_paid.rb
module Orders
  class MarkPaid
    def initialize(order_id)
      @order_id = order_id
    end

    def call
      order = Order.find(@order_id)
      return if order.paid?

      order.with_lock do
        order.update!(paid_at: Time.current, status: "paid")
      end

      PaymentConfirmationJob.perform_later(order.id)
      InventoryService.new(order).reserve!
      Rails.cache.delete("order:#{order.id}")
    end
  end
end

# app/jobs/payment_confirmation_job.rb
class PaymentConfirmationJob < ApplicationJob
  queue_as :payments

  retry_on Net::ReadTimeout, wait: :exponentially_longer, attempts: 5

  def perform(order_id)
    order = Order.find(order_id)
    PaymentGateway.confirm(order: order, idempotency_key: order.id)
  end
end

# app/models/order.rb
class Order < ApplicationRecord
  has_many :items, dependent: :destroy

  def total
    @total ||= items.sum(&:price)
  end
end
```

<!-- Ground truth: 5 subtle seeded issues. Harder than the previous
diff — no glaring SQL injection. Measured via finding_recall.
1. Race on paid? check: read-check-then-lock without recheck inside
   with_lock. Two concurrent calls both pass paid? check, both enter
   with_lock sequentially. Second one overwrites. Classic TOCTOU.
2. InventoryService.new(order).reserve! runs INSIDE the implicit
   transaction around the callback scope but AFTER the update — if
   reserve! raises, the update commits but inventory is never reserved.
   Also: bug re non-transactional boundary.
3. Rails.cache.delete AFTER perform_later: the job may run before the
   cache delete completes in a distributed setup; also the delete is
   not tied to the transaction (no after_commit).
4. perform_later uses order.id inside a transaction block — Iron Law
   violation: job may fire before commit. Should be after_commit.
5. Order#total uses @total memoization on a model instance — stale
   after add/remove item, and items.sum(&:price) loads ALL items
   into memory (should be items.sum(:price) for a DB-side sum). -->
