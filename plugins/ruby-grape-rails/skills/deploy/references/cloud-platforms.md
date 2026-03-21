# Cloud Platform Deployment Guides

Platform-specific deployment configurations for Rails applications.

## Heroku

```ruby
# Procfile
web: bundle exec puma -C config/puma.rb
worker: bundle exec solid_queue
release: bundle exec rails db:migrate
```

## AWS ECS/Fargate

```json
{
  "family": "myapp",
  "networkMode": "awsvpc",
  "containerDefinitions": [
    {
      "name": "web",
      "image": "myapp:latest",
      "portMappings": [{"containerPort": 3000}],
      "command": ["thrust", "bundle", "exec", "puma"],
      "environment": [
        {"name": "RAILS_ENV", "value": "production"}
      ],
      "secrets": [
        {"name": "RAILS_MASTER_KEY", "valueFrom": "arn:aws:secretsmanager:..."}
      ]
    }
  ]
}
```

## Fly.io

```toml
# fly.toml
app = "myapp"

[build]
  dockerfile = "Dockerfile"

[env]
  PORT = "3000"
  RAILS_ENV = "production"

[http_service]
  internal_port = 3000
  force_https = true
  auto_stop_machines = true
  auto_start_machines = true

[deploy]
  release_command = "bundle exec rails db:migrate"
```

## Kubernetes

```yaml
# deployment.yaml
livenessProbe:
  httpGet:
    path: /up
    port: 3000
  initialDelaySeconds: 10
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /up
    port: 3000
  initialDelaySeconds: 5
  periodSeconds: 10
```

## Docker Compose Health Checks

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:3000/up"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 10s
```
