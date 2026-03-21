# WaterDrop Producer

Standalone producer for high-throughput scenarios:

```ruby
gem 'waterdrop'
```

## Setup

```ruby
producer = WaterDrop::Producer.new

producer.setup do |config|
  config.kafka = {
    'bootstrap.servers': 'localhost:9092',
    'client.id': 'waterdrop_producer',
    'queue.buffering.max.messages': 1000,
    'queue.buffering.max.ms': 100,
    'batch.size': 16384,
    'compression.codec': 'gzip'
  }
end
```

## Production Patterns

```ruby
# Sync for critical operations
producer.produce_sync(
  topic: 'orders',
  payload: order.to_json,
  key: order.id
)

# Async for high throughput
producer.produce_async(
  topic: 'events',
  payload: event.to_json
)

# Batch produce
messages = events.map do |event|
  {
    topic: 'events',
    payload: event.to_json,
    key: event.user_id
  }
end

producer.produce_many_async(messages)
```

## Cleanup

```ruby
# Always close producer on shutdown
at_exit { producer.close }
```
