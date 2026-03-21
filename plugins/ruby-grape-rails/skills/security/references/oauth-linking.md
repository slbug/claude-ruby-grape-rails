# OAuth Account Linking Patterns

## Progressive Resolution Pattern

When a user authenticates via OAuth, resolve their identity in order:

```ruby
class OauthService
  def self.find_or_create_user_from_oauth(auth)
    email = auth.info.email
    provider = auth.provider.to_s
    uid = auth.uid.to_s

    # 1. Check for existing identity (same provider + uid)
    identity = UserIdentity.find_by(provider: provider, uid: uid)
    return identity.user if identity

    # 2. Check for existing user by email (link accounts)
    user = User.find_by(email: email)
    if user
      link_identity(user, auth)
      return user
    end

    # 3. Create new user with identity
    create_user_with_identity(auth)
  end

  private

  def self.link_identity(user, auth)
    UserIdentity.create!(
      user: user,
      provider: auth.provider.to_s,
      uid: auth.uid.to_s,
      provider_token: encrypt(auth.credentials.token),
      provider_refresh_token: encrypt(auth.credentials.refresh_token),
      provider_token_expires_at: auth.credentials.expires_at ? Time.at(auth.credentials.expires_at) : nil
    )
  end

  def self.create_user_with_identity(auth)
    user = User.create!(
      email: auth.info.email,
      name: auth.info.name,
      password: SecureRandom.hex(32)  # Random password - they'll use OAuth
    )
    
    link_identity(user, auth)
    user
  end

  def self.encrypt(value)
    return unless value
    Rails.application.encrypted(value)
  end
end
```

## Identity Schema

```ruby
# db/migrate/xxx_create_user_identities.rb
class CreateUserIdentities < ActiveRecord::Migration[7.1]
  def change
    create_table :user_identities do |t|
      t.string :provider, null: false
      t.string :uid, null: false
      # Encrypt tokens at rest with attr_encrypted or Rails encryption
      t.string :provider_token_ciphertext
      t.string :provider_refresh_token_ciphertext
      t.datetime :provider_token_expires_at
      t.references :user, null: false, foreign_key: { on_delete: :cascade }

      t.timestamps
    end

    add_index :user_identities, [:provider, :uid], unique: true
    add_index :user_identities, :user_id
  end
end

# app/models/user_identity.rb
class UserIdentity < ApplicationRecord
  belongs_to :user
  
  encrypts :provider_token, :provider_refresh_token
  
  validates :provider, :uid, presence: true
  validates :uid, uniqueness: { scope: :provider }
end

# app/models/user.rb
class User < ApplicationRecord
  has_many :identities, class_name: 'UserIdentity', dependent: :destroy
end
```

## Token Refresh Pattern

```ruby
class UserIdentity < ApplicationRecord
  def token_expired?
    return false unless provider_token_expires_at
    provider_token_expires_at < Time.current
  end

  def refresh_token_if_expired!
    return self unless token_expired?
    return self unless provider_refresh_token.present?

    # Provider-specific refresh logic
    new_token = refresh_oauth_token
    
    update!(
      provider_token: new_token[:token],
      provider_refresh_token: new_token[:refresh_token],
      provider_token_expires_at: new_token[:expires_at]
    )
    
    self
  rescue OAuth2::Error => e
    # Token refresh failed - user needs to re-authenticate
    Rails.logger.error("Token refresh failed for #{provider}: #{e.message}")
    nil
  end

  private

  def refresh_oauth_token
    case provider
    when 'google'
      refresh_google_token
    when 'github'
      refresh_github_token
    else
      raise "Unsupported provider: #{provider}"
    end
  end

  def refresh_google_token
    client = OAuth2::Client.new(
      ENV['GOOGLE_CLIENT_ID'],
      ENV['GOOGLE_CLIENT_SECRET'],
      site: 'https://oauth2.googleapis.com'
    )
    
    token = OAuth2::AccessToken.new(
      client,
      provider_token,
      refresh_token: provider_refresh_token
    )
    
    new_token = token.refresh!
    
    {
      token: new_token.token,
      refresh_token: new_token.refresh_token || provider_refresh_token,
      expires_at: Time.at(new_token.expires_at)
    }
  end
end
```

## Multiple Providers Per User

```ruby
class User < ApplicationRecord
  has_many :identities, dependent: :destroy

  def providers
    identities.pluck(:provider)
  end

  def unlink_identity(provider)
    identity = identities.find_by!(provider: provider)
    
    # Ensure user has another way to log in
    if encrypted_password.present? || identities.count > 1
      identity.destroy!
      true
    else
      errors.add(:base, "Cannot remove last authentication method")
      false
    end
  end
end
```

## Security Considerations

1. **Email verification** - Only link if OAuth provider verified the email
2. **Encrypt tokens** - Use Rails encrypted attributes or attr_encrypted
3. **GDPR consent** - May need explicit consent for new accounts
4. **Token scope** - Request minimal scopes needed
5. **Refresh token rotation** - Implement rotation if provider supports it

```ruby
class OauthService
  def self.email_verified?(auth)
    case auth.provider.to_s
    when 'google'
      auth.extra.raw_info['email_verified'] == true
    when 'github'
      # GitHub only returns verified emails
      auth.info.email.present?
    else
      false
    end
  end

  def self.find_or_create_user_from_oauth(auth)
    unless email_verified?(auth)
      return { error: :email_not_verified }
    end
    
    user = find_or_create_internal(auth)
    { success: true, user: user }
  end
end
```

## OAuth Controller

```ruby
class OauthCallbacksController < ApplicationController
  def create
    auth = request.env['omniauth.auth']
    
    result = OauthService.find_or_create_user_from_oauth(auth)
    
    if result[:success]
      session[:user_id] = result[:user].id
      redirect_to root_path, notice: 'Signed in successfully'
    else
      redirect_to login_path, alert: 'Could not sign in'
    end
  end

  def failure
    redirect_to login_path, alert: 'Authentication failed'
  end
end
```
