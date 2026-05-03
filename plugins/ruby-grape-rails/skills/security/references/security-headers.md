# Security Headers Reference

## Content Security Policy

```ruby
# config/initializers/content_security_policy.rb
Rails.application.config.content_security_policy do |policy|
  policy.default_src :self
  policy.script_src :self, -> { "'nonce-#{SecureRandom.base64(16)}'" }
  policy.style_src :self, -> { "'nonce-#{SecureRandom.base64(16)}'" }
  policy.img_src :self, :data
  policy.connect_src :self, -> { "wss://#{ENV['HOST']}" }
  policy.frame_ancestors :self
end

# In controller
class ApplicationController < ActionController::Base
  before_action :set_csp_nonce
  
  private
  
  def set_csp_nonce
    @csp_nonce = SecureRandom.base64(16)
    response.headers['Content-Security-Policy'] = build_csp_with_nonce(@csp_nonce)
  end
end
```

## CSRF Protection

Rails enables CSRF protection by default:

```ruby
# ApplicationController
class ApplicationController < ActionController::Base
  protect_from_forgery with: :exception
end
```

Forms automatically include token:

```erb
<%= form_with model: @user do |f| %>
  <!-- CSRF token automatically included -->
<% end %>
```

## Rate Limiting

Using `rack-attack` gem:

```ruby
# config/initializers/rack_attack.rb
class Rack::Attack
  throttle('req/ip', limit: 300, period: 5.minutes) do |req|
    req.ip unless req.path.start_with?('/assets')
  end
  
  throttle('login/ip', limit: 5, period: 20.seconds) do |req|
    if req.path == '/login' && req.post?
      req.ip
    end
  end
  
  throttle('api/user', limit: 1000, period: 1.hour) do |req|
    req.env['warden'].user&.id if req.path.start_with?('/api/')
  end
end

# Custom response
Rack::Attack.throttled_responder = lambda do |env|
  retry_after = (env['rack.attack.match_data'][:period] - env['rack.attack.match_data'][:epoch_time] % env['rack.attack.match_data'][:period]).to_i
  
  [429, {'Retry-After' => retry_after.to_s, 'Content-Type' => 'application/json'}, [{error: 'Rate limit exceeded'}.to_json]]
end
```

## Security Headers

```ruby
# config/application.rb
config.action_dispatch.default_headers = {
  'X-Frame-Options' => 'SAMEORIGIN',
  'X-Content-Type-Options' => 'nosniff',
  'X-XSS-Protection' => '1; mode=block',
  'Referrer-Policy' => 'strict-origin-when-cross-origin'
}

# Or in controller
class ApplicationController < ActionController::Base
  before_action :set_security_headers
  
  private
  
  def set_security_headers
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-Content-Type-Options'] = 'nosniff'
  end
end
```

## HSTS (HTTPS Strict Transport Security)

```ruby
# config/environments/production.rb
Rails.application.config.force_ssl = true
Rails.application.config.ssl_options = {
  hsts: {
    expires: 1.year,
    subdomains: true,
    preload: true
  }
}
```

## Security Audit Tools

Static analysis with Brakeman:

```bash
gem install brakeman
brakeman -o brakeman_report.html
```

Dependency audit with bundle-audit:

```bash
gem install bundler-audit
bundle-audit check --update
```

Wire both into CI in your app repo (e.g.
`.github/workflows/security.yml`).

## Security Checklist

- [ ] bcrypt/argon2 for password hashing (has_secure_password)
- [ ] Timing-safe authentication
- [ ] CSRF protection enabled
- [ ] Authorization in every controller action (Pundit/CanCanCan)
- [ ] Input validation via model validations
- [ ] No string interpolation in SQL queries
- [ ] HTML escaping (no raw with user content)
- [ ] CSP headers configured
- [ ] Secrets in credentials.yml.enc or env vars
- [ ] Rate limiting on sensitive endpoints
- [ ] Security headers set
- [ ] Brakeman in CI/CD
- [ ] Dependency audits
