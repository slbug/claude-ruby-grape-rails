---
name: karafka
description: Apache Kafka processing with Karafka for Ruby. Multi-threaded consumers, batch processing, error handling, Rails integration.
user-invocable: false
effort: medium
paths:
  - "app/{consumers,producers,message_handlers}/**"
  - karafka.rb
  - "lib/message_handlers/**"
  - "**/app/{consumers,producers,message_handlers}/**"
  - "**/karafka.rb"
  - "**/lib/message_handlers/**"
  - "{packs,engines,components}/*/{consumers,producers,message_handlers}/**"
  - "app/{packages,packs}/*/{consumers,producers,message_handlers}/**"
---
# Karafka

Apache Kafka for Ruby with high-performance multi-threaded processing.

## Iron Laws

1. **Process in batches when possible** - Better throughput
2. **Handle dead letter queues** - Don't lose failed messages
3. **Monitor lag and throughput** - Key operational metrics
4. **Use idempotent consumers** - Safe to reprocess
5. **Commit offsets after processing** - At-least-once delivery
6. **Partition by business key** - Preserve ordering

## Installation

```ruby
gem 'karafka', '~> 2.5'
gem 'karafka-web'  # For Web UI
```

**Note:** Karafka 2.5+ is the current stable release. Check [karafka.io](https://karafka.io) for the latest version.

## Basic Setup

```ruby
# karafka.rb
class KarafkaApp < Karafka::App
  setup do |config|
    config.kafka = {
      'bootstrap.servers': ENV['KAFKA_BROKERS'],
      'client.id': 'my_app'
    }
    config.consumer_persistence = true
  end
  
  routes.draw do
    topic :orders do
      consumer OrdersConsumer
    end
    
    topic :payments do
      consumer PaymentsConsumer
    end
  end
end

KarafkaApp.boot!
```

## Consumer

```ruby
class OrdersConsumer < ApplicationConsumer
  def consume
    # Batch processing (recommended)
    Order.insert_all(messages.payloads)
    mark_as_consumed(messages.last)
    
    # Or individual processing
    messages.each do |message|
      process_payment(message.payload)
      mark_as_consumed(message)
    end
  end
end

class ApplicationConsumer < Karafka::BaseConsumer
  private
  
  def mark_as_consumed(message)
    consumer.mark_as_consumed(message)
  end
end
```

## Producing Messages

```ruby
# Sync (for critical messages)
Karafka.producer.produce_sync(
  topic: 'orders',
  payload: order.to_json,
  key: order.id  # Partition key
)

# Async (for high throughput)
Karafka.producer.produce_async(
  topic: 'orders',
  payload: order.to_json,
  key: order.id
)

# Batch
messages = orders.map { |o| { topic: 'orders', payload: o.to_json, key: o.id } }
Karafka.producer.produce_many_async(messages)
```

## Error Handling

```ruby
class OrdersConsumer < ApplicationConsumer
  def consume
    messages.each do |message|
      begin
        process_message(message)
        mark_as_consumed(message)
      rescue => e
        send_to_dlq(message, e)
        mark_as_consumed(message)
      end
    end
  end
  
  private
  
  def send_to_dlq(message, error)
    Karafka.producer.produce_sync(
      topic: 'orders_dlq',
      payload: message.payload.merge(
        error: error.message,
        failed_at: Time.current
      )
    )
  end
end
```

## Dead Letter Queue

```ruby
routes.draw do
  topic :orders do
    consumer OrdersConsumer
    dead_letter_queue topic: 'orders_dlq', max_retries: 3
  end
  
  topic :orders_dlq do
    consumer DlqConsumer
  end
end
```

## Consumer Groups

```ruby
routes.draw do
  consumer_group :orders_group do
    topic :orders do
      consumer OrdersConsumer
    end
    
    topic :order_updates do
      consumer OrderUpdatesConsumer
    end
  end
  
  consumer_group :payments_group do
    topic :payments do
      consumer PaymentsConsumer
    end
  end
end
```

## Rails Integration

### ActiveJob Backend

```ruby
# config/application.rb
config.active_job.queue_adapter = :karafka

Karafka::ActiveJob::JobAdapter.setup

class ProcessOrderJob < ActiveJob::Base
  queue_as :orders
  
  def perform(order_id)
    Order.find(order_id).process!
  end
end

# Enqueue
ProcessOrderJob.perform_later(order.id)
```

### Routes Setup

```ruby
# config/routes.rb
mount Karafka::Web::App, at: '/karafka'
```

## Web UI

```ruby
Karafka::Web.setup do |config|
  config.ui.sessions.secret = ENV['KARAFKA_UI_SECRET']
end
```

Features:

- Consumer group status
- Partition offsets
- Message throughput
- Error rates
- Consumer lag monitoring

## Monitoring

### Consumer Lag

```ruby
Karafka::Admin.lag('orders_group', 'orders')
```

### Custom Metrics

```ruby
def consume
  messages.each do |message|
    start_time = Time.current
    process_message(message)
    
    StatsD.measure('kafka.processing_time', Time.current - start_time, tags: {
      topic: topic.name,
      consumer: self.class.name
    })
    
    mark_as_consumed(message)
  end
end
```

## Configuration Options

```ruby
topic :orders do
  consumer OrdersConsumer
  
  # Batch settings
  max_messages 100
  max_wait_time 1000
  
  # Offset management
  manual_offset_management false  # Auto-commit (default)
  
  # Error handling
  dead_letter_queue topic: 'orders_dlq', max_retries: 3
end
```

## Testing

```ruby
RSpec.describe OrdersConsumer do
  subject(:consumer) { described_class.new }
  
  let(:message) do
    Karafka::Messages::Message.new(
      { 'id' => 1, 'status' => 'created' },
      OpenStruct.new(topic: 'orders', partition: 0, offset: 0)
    )
  end
  
  it 'processes the message' do
    expect { consumer.on_message(message) }
      .to change(Order, :count).by(1)
  end
end
```

## Deployment

### Docker

```dockerfile
FROM ruby:3.4-slim
WORKDIR /app
COPY Gemfile* ./
RUN bundle install
COPY . .
CMD ["bundle", "exec", "karafka", "server"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: karafka-consumer
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: consumer
        image: myapp:latest
        command: ["bundle", "exec", "karafka", "server"]
        env:
        - name: KAFKA_BROKERS
          value: "kafka:9092"
```

## References

- `references/batch-processing.md` — Advanced batch processing patterns
- `references/deployment-guide.md` — Production deployment strategies
- `references/waterdrop-producer.md` — Standalone producer configuration
