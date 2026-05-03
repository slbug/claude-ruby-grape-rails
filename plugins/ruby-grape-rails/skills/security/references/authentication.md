# Authentication Patterns Reference

## Devise (Recommended)

```ruby
# Gemfile
gem 'devise'

# Install
rails generate devise:install
rails generate devise User

# Configure
# config/initializers/devise.rb
Devise.setup do |config|
  config.mailer_sender = 'please-change-me@example.com'
  config.pepper = ENV['DEVISE_PEPPER']
  config.stretches = Rails.env.test? ? 1 : 12
end
```

## Custom Authentication with has_secure_password

```ruby
class User < ApplicationRecord
  has_secure_password
  
  validates :email, presence: true, uniqueness: { case_sensitive: false }
  validates :password, length: { minimum: 12 }, if: :password_required?
end

class SessionController < ApplicationController
  def create
    user = User.find_by(email: params[:email])
    
    if user&.authenticate(params[:password])
      # Timing-safe authentication (bcrypt handles this)
      session[:user_id] = user.id
      redirect_to root_path, notice: 'Signed in successfully'
    else
      # Don't reveal if user exists
      flash.now[:alert] = 'Invalid email or password'
      render :new
    end
  end
end
```

## Session Configuration

```ruby
# config/initializers/session_store.rb
Rails.application.config.session_store :cookie_store,
  key: '_my_app_session',
  secure: Rails.env.production?,  # HTTPS only
  httponly: true,                   # Not accessible via JS
  same_site: :lax                   # CSRF protection

# For API-only apps, use token-based:
Rails.application.config.session_store :disabled
```

## Remember Me (Secure)

```ruby
class SessionController < ApplicationController
  def create
    user = User.authenticate(params[:email], params[:password])
    
    if user
      session[:user_id] = user.id
      
      if params[:remember_me]
        # Generate secure token
        token = SecureRandom.urlsafe_base64(32)
        user.update!(remember_token: token, remember_token_expires_at: 30.days.from_now)
        cookies.encrypted[:remember_token] = {
          value: token,
          expires: 30.days,
          httponly: true,
          secure: Rails.env.production?
        }
      end
      
      redirect_to root_path
    end
  end
end

class ApplicationController < ActionController::Base
  before_action :authenticate_user
  
  private
  
  def authenticate_user
    if session[:user_id]
      @current_user = User.find_by(id: session[:user_id])
    elsif cookies.encrypted[:remember_token]
      @current_user = User.find_by(
        remember_token: cookies.encrypted[:remember_token],
        remember_token_expires_at: Time.current..
      )
      session[:user_id] = @current_user.id if @current_user
    end
  end
end
```

## MFA with ROTP

```ruby
# Gemfile
gem 'rotp'

class User < ApplicationRecord
  def enable_mfa!
    self.mfa_secret = ROTP::Base32.random
    self.mfa_enabled = false  # Requires verification first
    save!
  end
  
  def verify_mfa(code)
    totp = ROTP::TOTP.new(mfa_secret)
    totp.verify(code, drift_behind: 30)  # 30 second tolerance
  end
  
  def mfa_qr_code_uri
    ROTP::TOTP.new(mfa_secret).provisioning_uri(email, issuer_name: "MyApp")
  end
end
```

## Secrets Management

### Credentials (Rails 6+)

Edit encrypted credentials (default or production-specific):

```bash
EDITOR=vim bin/rails credentials:edit
EDITOR=vim bin/rails credentials:edit --environment production
```

```yaml
# config/credentials.yml.enc (access via Rails.application.credentials)
secret_key_base: ...
database:
  password: ...
aws:
  access_key_id: ...
  secret_access_key: ...
```

```ruby
# config/database.yml
production:
  password: <%= Rails.application.credentials.database[:password] %>
```

### Environment Variables

```ruby
# config/application.rb or initializers
Rails.application.credentials.secret_key_base = ENV['SECRET_KEY_BASE']
```

## Sensitive Data Redaction

```ruby
class User < ApplicationRecord
  # Exclude from inspect/logs
  def inspect
    "#<User id: #{id}, email: #{email}>"
  end
  
  # Or use filter_attributes (Rails 7+)
  self.filter_attributes = [:password_digest, :mfa_secret]
end

# Filter in logs
Rails.application.config.filter_parameters += [:password, :token, :credit_card]
```

## Magic Link Authentication

```ruby
class MagicLink < ApplicationRecord
  belongs_to :user
  
  before_create :generate_token
  
  scope :valid, -> { where('expires_at > ?', Time.current) }
  
  def generate_token
    self.token = SecureRandom.urlsafe_base64(32)
    self.expires_at = 24.hours.from_now
  end
  
  def self.verify(token)
    valid.find_by(token: token)
  end
end

class MagicLinksController < ApplicationController
  def create
    user = User.find_by(email: params[:email])
    
    if user
      MagicLink.create!(user: user)
      UserMailer.magic_link(user).deliver_later
    end
    
    # Always show same message (don't reveal if user exists)
    flash[:notice] = 'Check your email for the magic link'
    redirect_to root_path
  end
  
  def show
    magic_link = MagicLink.verify(params[:token])
    
    if magic_link
      session[:user_id] = magic_link.user_id
      magic_link.destroy  # One-time use
      redirect_to root_path, notice: 'Signed in successfully'
    else
      redirect_to login_path, alert: 'Invalid or expired link'
    end
  end
end
```
