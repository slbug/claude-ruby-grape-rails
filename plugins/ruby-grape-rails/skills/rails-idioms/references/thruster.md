## Thruster Integration

Thruster is the default production server wrapper in Rails 8:

```dockerfile
# Dockerfile
FROM ruby:3.4
# ...
# Thruster is included in the official Rails Docker image
CMD ["./bin/thrust", "./bin/rails", "server"]
```

Or run directly: `bundle exec thrust rails server`.

### Thruster Features

- **HTTP/2 support** - Automatic HTTP/2 with HTTP/1.1 fallback
- **Automatic HTTPS** - Let's Encrypt integration
- **X-Sendfile** - Efficient static file serving
- **Gzip compression** - Built-in compression
- **HTTP caching** - Static asset caching headers

```yaml
# docker-compose.yml
services:
  web:
    build: .
    environment:
      THRUSTER_HOST: 0.0.0.0
      THRUSTER_PORT: 80
      THRUSTER_TLS: "true"
      THRUSTER_TLS_AUTO: "true"
```
