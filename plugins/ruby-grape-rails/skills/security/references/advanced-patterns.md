# Advanced Security Patterns

Extends core security skill with SSRF prevention, secrets management, and supply chain security.

## Contents

- [SSRF Prevention](#ssrf-prevention-server-side-request-forgery)
- [Secrets Management](#secrets-management)
- [Supply Chain Security](#supply-chain-security)
- [Extended Security Checklist](#extended-security-checklist)
- [CORS Configuration](#cors-configuration)
- [Safe Deserialization](#safe-deserialization)
- [File Upload Content-Type Validation](#file-upload-content-type-validation)

## SSRF Prevention (Server-Side Request Forgery)

### The Risk

User-controlled URLs can access internal services:

```ruby
# VULNERABLE
def fetch_url(url)
  response = HTTP.get(url)  # User passes http://169.254.169.254/metadata
end
```

### Prevention Patterns

#### URL Allowlist

```ruby
class SafeUrlFetcher
  ALLOWED_HOSTS = %w[api.example.com cdn.example.com].freeze

  def self.fetch(url)
    uri = URI.parse(url)

    unless ALLOWED_HOSTS.include?(uri.host)
      raise ArgumentError, "Host not allowed: #{uri.host}"
    end

    HTTP.get(url)
  end
end
```

#### Block Internal IPs

```ruby
class SSRFProtection
  BLOCKED_RANGES = [
    IPAddr.new('127.0.0.0/8'),      # Loopback
    IPAddr.new('10.0.0.0/8'),       # Private
    IPAddr.new('172.16.0.0/12'),    # Private
    IPAddr.new('192.168.0.0/16'),   # Private
    IPAddr.new('169.254.0.0/16'),   # Link-local
    IPAddr.new('169.254.169.254/32') # Cloud metadata
  ].freeze

  def self.safe_url?(url)
    uri = URI.parse(url)
    return false unless uri.host

    begin
      ip = Resolv.getaddress(uri.host)
      ip_addr = IPAddr.new(ip)
      
      BLOCKED_RANGES.none? { |range| range.include?(ip_addr) }
    rescue Resolv::ResolvError
      false
    end
  end
end
```

#### Webhook Validation

```ruby
class WebhookService
  def self.register(url)
    unless SSRFProtection.safe_url?(url)
      return { error: :unsafe_url }
    end
    
    # Verify URL responds before saving
    response = HTTP.timeout(5).head(url)
    
    unless response.status.success?
      return { error: :unreachable }
    end
    
    Webhook.create!(url: url)
  end
end
```

## Secrets Management

### Rails Credentials (Recommended)

```bash
# Edit encrypted credentials
EDITOR=vim bin/rails credentials:edit

# Or for production-specific
EDITOR=vim bin/rails credentials:edit --environment production
```

```yaml
# config/credentials.yml.enc (access via Rails.application.credentials)
secret_key_base: ...
aws:
  access_key_id: ...
  secret_access_key: ...
stripe:
  secret_key: ...
  webhook_secret: ...
```

```ruby
# Usage
Rails.application.credentials.aws[:access_key_id]
Rails.application.credentials.stripe[:secret_key]
```

### Environment Variables

```ruby
# config/application.rb or initializers
Rails.application.credentials.secret_key_base = ENV['SECRET_KEY_BASE']
```

### Secrets Rotation Pattern

```ruby
class SecretsCache
  def self.get(key)
    Rails.cache.fetch("secret:#{key}", expires_in: 1.hour) do
      fetch_from_vault(key)
    end
  end

  def self.refresh!
    Rails.cache.delete_matched("secret:*")
  end

  private

  def self.fetch_from_vault(key)
    # Fetch from Vault/AWS Secrets Manager/etc.
    VaultClient.read(key)
  end
end

# Schedule refresh
Sidekiq::Cron::Job.create(
  name: 'Refresh Secrets',
  cron: '0 */6 * * *',  # Every 6 hours
  class: 'RefreshSecretsJob'
)
```

### Audit Script

Two passes over `app/` and `config/` Ruby files:

- Pattern 1: `sk_live|sk_test|aws_secret|password.*=`
- Pattern 2: `api_key|secret_key|private_key`

For `.env` inspection: filter out comments (`^#`) and blank lines
(`^$`).

## Supply Chain Security

### Dependency Auditing

```bash
# Check for known vulnerabilities
gem install bundler-audit
bundle-audit check --update

# Add to CI
bundle-audit check || exit 1
```

### Gemfile Security

```ruby
# Pin specific versions to avoid unexpected updates
gem 'rails', '~> 7.1.0'

# Use only HTTPS sources
source 'https://rubygems.org'

# Add security group for development only
group :development do
  gem 'brakeman', require: false
  gem 'bundler-audit', require: false
end
```

### Dependency Review Checklist

Before adding new dependency:

- [ ] Check rubygems.org download count (popularity)
- [ ] Check GitHub stars/activity
- [ ] Check last commit date
- [ ] Check open security issues
- [ ] Review permissions/capabilities needed
- [ ] Check transitive dependencies

```bash
# Check what a gem brings in
bundle viz --format png
```

### Minimal Dependencies

```ruby
# Prefer standard library
# BAD - unnecessary dep for simple JSON
gem 'json_pure'

# GOOD - use built-in
require 'json'
JSON.parse(data)
```

## Extended Security Checklist

Add to security review:

### SSRF

- [ ] User-controlled URLs validated
- [ ] Internal IPs blocked
- [ ] DNS rebinding considered
- [ ] Webhook URLs verified

### Secrets

- [ ] No hardcoded secrets in code
- [ ] Rails credentials or ENV vars used
- [ ] .env files in .gitignore
- [ ] Rotation mechanism for long-lived secrets

### Supply Chain

- [ ] `bundle-audit` clean
- [ ] Gemfile.lock committed
- [ ] New gems reviewed
- [ ] Regular dependency updates

### CORS

- [ ] Origins explicitly allowlisted (never `*` with credentials)
- [ ] Credentials mode requires specific origins
- [ ] Preflight caching configured

### Additional Vectors

- [ ] XML parsing: external entities disabled (XXE)
- [ ] File paths: sanitized (path traversal)
- [ ] YAML: safe_load only (psych vulnerability)
- [ ] Rate limiting on expensive operations
- [ ] File uploads: validate content-type, not just extension
- [ ] State-changing GET requests: never (CSRF bypass)

## CORS Configuration

```ruby
# config/initializers/cors.rb
Rails.application.config.middleware.insert_before 0, Rack::Cors do
  allow do
    # SAFE: Explicit origins
    origins 'https://app.example.com', 'https://admin.example.com'
    
    # VULNERABLE: Overly broad regex
    # origins /^https?:\/\/.*example\.com$/
    # Matches: https://evil-example.com (attacker domain!)
    
    resource '*',
      headers: :any,
      methods: [:get, :post, :put, :patch, :delete, :options, :head],
      credentials: true  # Only with explicit origins above
  end
end
```

## Safe Deserialization

```ruby
# VULNERABLE: arbitrary code execution
YAML.load(user_data)
Marshal.load(user_data)

# SAFE: safe_load only
YAML.safe_load(user_data, permitted_classes: [Date, Time, Symbol])

# Use JSON instead when possible
JSON.parse(user_data)
```

## File Upload Content-Type Validation

```ruby
class User < ApplicationRecord
  has_one_attached :avatar
  
  validate :validate_image_content
  
  MAGIC_BYTES = {
    '\xFF\xD8\xFF' => 'image/jpeg',
    '\x89PNG' => 'image/png',
    'GIF' => 'image/gif'
  }.freeze
  
  def validate_image_content
    return unless avatar.attached?
    
    avatar.download do |file|
      header = file.read(4)
      
      detected = MAGIC_BYTES.find { |magic, _| header.include?(magic) }
      
      unless detected && detected[1] == avatar.content_type
        errors.add(:avatar, 'File content does not match declared type')
      end
    end
  end
end
```

Without content-type validation, attackers can upload HTML files
with `.jpg` extension that execute XSS when served.
