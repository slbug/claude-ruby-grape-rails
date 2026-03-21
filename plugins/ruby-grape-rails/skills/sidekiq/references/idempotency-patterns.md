# Idempotency Patterns

## State Check Pattern

Check if work was already done before processing:

```ruby
class ProcessPaymentJob
  include Sidekiq::Job

  def perform(payment_id)
    payment = Payment.find(payment_id)
    return if payment.processed?
    
    payment.with_lock do
      return if payment.processed?
      payment.process!
    end
  end
end
```

## Upsert Pattern

Use `find_or_create_by` for safe creation:

```ruby
class CreateInvoiceJob
  include Sidekiq::Job

  def perform(order_id)
    order = Order.find(order_id)
    
    # Safe to retry - finds existing if already created
    Invoice.find_or_create_by!(order: order) do |invoice|
      invoice.amount = order.total
      invoice.due_date = 30.days.from_now
    end
  end
end
```

## UUID Deduplication

Store processed UUIDs for exactly-once semantics:

```ruby
class WebhookProcessorJob
  include Sidekiq::Job

  def perform(event_id, payload)
    # Check if we've processed this event
    return if ProcessedEvent.exists?(event_id: event_id)
    
    ProcessedEvent.create!(event_id: event_id)
    
    # Process webhook
    process_payload(payload)
  rescue ActiveRecord::RecordNotUnique
    # Another worker already processed it
    nil
  end
end
```

## Idempotency Key Pattern

For external API calls:

```ruby
class SyncToExternalServiceJob
  include Sidekiq::Job

  def perform(record_id)
    record = Record.find(record_id)
    
    # Use idempotency key for API call
    ExternalAPI.create(
      record.data,
      idempotency_key: "#{self.class.name}:#{record_id}:#{record.updated_at.to_i}"
    )
  end
end
```
