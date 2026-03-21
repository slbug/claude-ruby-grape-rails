# Advanced Batch Processing

## Batch Insert Pattern

```ruby
class OrdersConsumer < ApplicationConsumer
  def consume
    # Bulk insert for better performance
    Order.insert_all(
      messages.payloads.map { |payload| 
        payload.merge(created_at: Time.current, updated_at: Time.current)
      }
    )
    
    mark_as_consumed(messages.last)
  end
end
```

## Transactional Processing

```ruby
class PaymentConsumer < ApplicationConsumer
  def consume
    ActiveRecord::Base.transaction do
      messages.each do |message|
        process_payment(message.payload)
        mark_as_consumed(message)
      end
    end
  rescue => e
    # Transaction rolls back, messages not marked as consumed
    # Will be retried
    raise
  end
end
```

## Exactly-Once Semantics

```ruby
class IdempotentConsumer < ApplicationConsumer
  def consume
    messages.each do |message|
      # Use message key as idempotency key
      Event.find_or_create_by!(id: message.key) do |event|
        event.payload = message.payload
        event.processed_at = Time.current
      end
      
      mark_as_consumed(message)
    end
  end
end
```
