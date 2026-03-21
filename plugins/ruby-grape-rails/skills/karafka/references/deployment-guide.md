# Production Deployment Guide

## Configuration

```ruby
class KarafkaApp < Karafka::App
  setup do |config|
    config.kafka = {
      'bootstrap.servers': ENV.fetch('KAFKA_BROKERS'),
      'client.id': ENV.fetch('KAFKA_CLIENT_ID'),
      'security.protocol': 'ssl',
      'ssl.ca.location': ENV.fetch('KAFKA_SSL_CA'),
      'ssl.certificate.location': ENV.fetch('KAFKA_SSL_CERT'),
      'ssl.key.location': ENV.fetch('KAFKA_SSL_KEY'),
      'group.id': 'my_app_consumers'
    }
  end
end
```

## Scaling

Scale by increasing partitions and consumers:

```yaml
# Scale consumers to match partitions
replicas: 6  # For 6 partitions
template:
  spec:
    containers:
    - name: consumer
      resources:
        requests:
          memory: "1Gi"
          cpu: "500m"
        limits:
          memory: "2Gi"
          cpu: "1000m"
```

## Health Checks

```ruby
# config/initializers/karafka.rb
Karafka.monitor.subscribe('connection.listener.fetch_loop') do |event|
  # Custom health check logic
  StatsD.increment('karafka.fetch_loop')
end
```

## Graceful Shutdown

Karafka handles SIGTERM gracefully:

- Stops fetching new messages
- Completes current batch
- Commits offsets
- Exits cleanly

```yaml
# Kubernetes graceful shutdown
terminationGracePeriodSeconds: 60
```
