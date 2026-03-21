# Input Validation Patterns Reference

## Model Validations (Primary Defense)

```ruby
class User < ApplicationRecord
  # Registration validations
  validates :email, presence: true, 
                    format: { with: URI::MailTo::EMAIL_REGEXP },
                    uniqueness: { case_sensitive: false }
  validates :username, presence: true,
                       length: { in: 3..30 },
                       format: { with: /\A[a-zA-Z0-9_]+\z/ },
                       exclusion: { in: RESERVED_USERNAMES }
  validates :password, presence: true,
                       length: { in: 12..72 },
                       if: :password_required?
end

class UserRegistration
  def self.register(params)
    user = User.new(params)
    
    if user.valid?
      user.save!
      { success: true, user: user }
    else
      { success: false, errors: user.errors }
    end
  end
end
```

## File Upload Validation

```ruby
class User < ApplicationRecord
  has_one_attached :avatar
  
  validate :avatar_validation
  
  MAX_FILE_SIZE = 10.megabytes
  ALLOWED_EXTENSIONS = %w[jpg jpeg png gif pdf]
  
  def avatar_validation
    return unless avatar.attached?
    
    unless avatar.content_type.in?(%w[image/jpeg image/png image/gif application/pdf])
      errors.add(:avatar, 'must be JPG, PNG, GIF, or PDF')
    end
    
    unless avatar.byte_size <= MAX_FILE_SIZE
      errors.add(:avatar, "must be less than #{MAX_FILE_SIZE / 1.megabyte}MB")
    end
    
    # Magic bytes validation (first few bytes of file)
    unless valid_magic_bytes?(avatar)
      errors.add(:avatar, 'file type does not match extension')
    end
  end
  
  private
  
  def valid_magic_bytes?(file)
    file.open do |f|
      header = f.read(4)
      case avatar.content_type
      when 'image/jpeg' then header.start_with?("\xFF\xD8\xFF")
      when 'image/png'  then header == "\x89PNG"
      when 'image/gif'  then header.start_with?("GIF")
      when 'application/pdf' then header.start_with?("%PDF")
      else true
      end
    end
  end
end
```

## Path Traversal Prevention

```ruby
class FileController < ApplicationController
  def download
    # User provides relative path
    user_path = params[:path]
    
    # Sanitize and validate
    safe_path = File.expand_path(user_path, Rails.root.join('uploads'))
    
    unless safe_path.start_with?(Rails.root.join('uploads').to_s)
      head :forbidden
      return
    end
    
    send_file safe_path
  end
end
```

## SQL Injection Prevention

```ruby
# ✅ SAFE: Parameterized queries
User.where("name = ?", user_input)
User.where(name: user_input)  # Even safer

# ✅ SAFE: Arel (safe query building)
User.where(User.arel_table[:name].eq(user_input))

# ❌ VULNERABLE: String interpolation
User.where("name = '#{user_input}'")

# ❌ VULNERABLE: Raw SQL
ActiveRecord::Base.connection.execute("SELECT * FROM users WHERE name = '#{user_input}'")
```

## XSS Prevention

### Template Escaping

```erb
<!-- ✅ SAFE: Auto-escaped -->
<%= @user_content %>

<!-- ❌ VULNERABLE: Raw output -->
<%= raw @user_content %>
<%= @user_content.html_safe %>
```

### HTML Sanitization

Using `rails-html-sanitizer` (included in Rails):

```ruby
class Comment < ApplicationRecord
  ALLOWED_TAGS = %w[p br strong em ul ol li h1 h2 h3 blockquote code pre].freeze
  ALLOWED_ATTRIBUTES = %w[].freeze
  
  before_save :sanitize_content
  
  private
  
  def sanitize_content
    self.content = Rails::Html::SafeListSanitizer.new.sanitize(
      content,
      tags: ALLOWED_TAGS,
      attributes: ALLOWED_ATTRIBUTES
    )
  end
end
```

## Parameter Filtering

```ruby
# config/initializers/filter_parameter_logging.rb
Rails.application.config.filter_parameters += [
  :password,
  :password_confirmation,
  :credit_card,
  :ssn,
  :token,
  :secret,
  :api_key
]
```

## Strong Parameters

```ruby
class UsersController < ApplicationController
  def create
    user = User.new(user_params)
    # ...
  end
  
  private
  
  def user_params
    params.require(:user).permit(:name, :email, :password)
  end
  
  def admin_params
    # Only admins can set these
    params.require(:user).permit(:role, :admin_notes)
  end
end
```

## Command Injection Prevention

```ruby
# ❌ VULNERABLE
system("convert #{user_path} output.jpg")

# ✅ SAFE: Parameterized
system("convert", user_path, "output.jpg")

# ✅ SAFE: Use library
MiniMagick::Image.open(user_path).format("jpg").write("output.jpg")
```

## Open Redirect Prevention

```ruby
class SessionsController < ApplicationController
  def create
    # ... authenticate ...
    
    # ❌ VULNERABLE
    redirect_to params[:return_to]
    
    # ✅ SAFE: Whitelist
    safe_return = params[:return_to]
    if safe_return.present? && safe_return.start_with?(root_url)
      redirect_to safe_return
    else
      redirect_to root_path
    end
  end
end
```

## Validation Helper

```ruby
class ApplicationController < ActionController::Base
  private
  
  def validate_email_format(email)
    email.match?(URI::MailTo::EMAIL_REGEXP)
  end
  
  def sanitize_filename(filename)
    # Remove path traversal attempts
    filename.gsub!(/^[.\/]+/, '')
    # Add random prefix to prevent overwrites
    "#{SecureRandom.hex(8)}_#{filename}"
  end
end
```
