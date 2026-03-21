# Rate Limiting Patterns

## Composite Key Strategy

Rate limit on multiple dimensions to prevent abuse while allowing legitimate use:

```ruby
class RateLimit
  # Magic link: limit by IP AND email hash (prevent enumeration)
  def self.check_magic_link(ip, email)
    email_hash = Digest::SHA256.hexdigest(email)
    
    check("magic_link:ip:#{ip}", 10, 15.minutes) &&
      check("magic_link:email:#{email_hash}", 3, 1.hour)
  end

  # API: limit by user AND global IP
  def self.check_api(user_id, ip)
    check("api:user:#{user_id}", 100, 1.minute) &&
      check("api:ip:#{ip}", 1000, 1.minute)
  end

  # AI tokens: separate call limit from token limit
  def self.check_ai_generation(user_id, estimated_tokens)
    check("ai:calls:#{user_id}", 50, 1.hour) &&
      check_tokens("ai:tokens:#{user_id}", estimated_tokens, 100_000, 24.hours)
  end

  private

  def self.check(key, limit, window)
    # Using rack-attack or redis directly
    Rack::Attack.cache.count(key, window) <= limit
  end

  def self.check_tokens(key, tokens, limit, window)
    # For token-based limiting, use Redis to track cumulative usage
    current = Redis.current.incrby("ratelimit:#{key}", tokens)
    Redis.current.expire("ratelimit:#{key}", window.to_i) if current == tokens
    current <= limit
  end
end
```

## Rack::Attack Rate Limiting

```ruby
# config/initializers/rack_attack.rb
class Rack::Attack
  class Request < ::Rack::Request
    def remote_ip
      @remote_ip ||= (env['HTTP_X_FORWARDED_FOR'] || env['REMOTE_ADDR']).to_s.split(',').first.strip
    end
  end

  throttle('req/ip', limit: 300, period: 5.minutes) do |req|
    req.remote_ip unless req.path.start_with?('/assets')
  end

  # API throttling with headers
  throttle('api/ip', limit: 100, period: 1.minute) do |req|
    req.remote_ip if req.path.start_with?('/api/')
  end

  # Authenticated user throttling
  throttle('api/user', limit: 1000, period: 1.hour) do |req|
    req.env['warden'].user&.id if req.path.start_with?('/api/')
  end

  # Login attempts
  throttle('login/ip', limit: 5, period: 15.minutes) do |req|
    req.remote_ip if req.path == '/login' && req.post?
  end
end

# Custom response with headers
Rack::Attack.throttled_responder = lambda do |env|
  retry_after = (env['rack.attack.match_data'][:period] - Time.now.to_i % env['rack.attack.match_data'][:period])
  
  [
    429,
    {
      'Content-Type' => 'application/json',
      'Retry-After' => retry_after.to_s,
      'X-RateLimit-Limit' => env['rack.attack.match_data'][:limit].to_s,
      'X-RateLimit-Remaining' => '0'
    },
    [{ error: 'Rate limit exceeded' }.to_json]
  ]
end
```

## Controller-Level Rate Limiting

```ruby
class Api::BaseController < ApplicationController
  before_action :check_rate_limit
  
  private
  
  def check_rate_limit
    key = "api:#{current_user&.id || request.remote_ip}"
    
    unless RateLimit.check(key, 1000, 1.hour)
      render json: { error: 'Rate limit exceeded' }, status: :too_many_requests
    end
  end
end
```

## Service-Level Rate Limiting

```ruby
class MagicLinkService
  def self.send(email, ip)
    return { error: :rate_limited } unless RateLimit.check_magic_link(ip, email)
    
    user = User.find_by(email: email)
    return { error: :not_found } unless user
    
    token = generate_token(user)
    UserMailer.magic_link(user, token).deliver_later
    
    { success: true }
  end
end

class AuthenticationService
  def self.login(email, password, ip)
    # Rate limit by IP for failed attempts
    unless RateLimit.check("login:ip:#{ip}", 10, 15.minutes)
      return { error: :rate_limited }
    end
    
    user = User.find_by(email: email)
    
    if user&.authenticate(password)
      # Reset rate limit on success
      Rack::Attack.cache.delete("login:ip:#{ip}")
      { success: true, user: user }
    else
      { error: :invalid_credentials }
    end
  end
end
```

## Strategies by Use Case

| Use Case | Key Strategy | Limit | Window |
|----------|-------------|-------|--------|
| Login attempts | IP | 10 | 15 min |
| Magic link | IP + email hash | 3/email, 10/IP | 1h/15m |
| Password reset | IP + email hash | 3/email | 1 hour |
| API (authenticated) | User ID | 1000 | 1 min |
| API (public) | IP | 100 | 1 min |
| AI generation | User (calls + tokens) | 50 calls, 100k tokens | 1h/24h |
| File upload | User | 10 | 1 hour |
| Email sending | User | 100 | 24 hours |

## Custom Redis-Based Limiter

```ruby
class RedisRateLimiter
  def initialize(redis: Redis.current)
    @redis = redis
  end

  def check(key, limit, window)
    current = @redis.incr("ratelimit:#{key}")
    @redis.expire("ratelimit:#{key}", window.to_i) if current == 1
    
    if current > limit
      @redis.decr("ratelimit:#{key}")
      false
    else
      true
    end
  end

  def remaining(key, limit)
    current = @redis.get("ratelimit:#{key}").to_i
    [limit - current, 0].max
  end

  def reset(key)
    @redis.del("ratelimit:#{key}")
  end
end
```

## Testing Rate Limits

```ruby
RSpec.describe "Rate limiting", type: :request do
  before do
    # Clear rate limit buckets
    Rack::Attack.cache.store.clear
  end

  it "blocks after limit exceeded" do
    ip = "127.0.0.1"
    
    # First 10 should pass
    10.times do
      post login_path, params: { email: "test@example.com" }, headers: { 'REMOTE_ADDR' => ip }
      expect(response).not_to have_http_status(:too_many_requests)
    end
    
    # 11th should fail
    post login_path, params: { email: "test@example.com" }, headers: { 'REMOTE_ADDR' => ip }
    expect(response).to have_http_status(:too_many_requests)
  end
end
```

## Configuration

```ruby
# config/initializers/rack_attack.rb
# Development - log but don't block
Rack::Attack.enabled = false if Rails.env.development?

# Redis backend for distributed systems
Rack::Attack.cache.store = ActiveSupport::Cache::RedisCacheStore.new(
  url: ENV.fetch('REDIS_URL', 'redis://localhost:6379/0')
)
```
