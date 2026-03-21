# Service Object Patterns Reference

## Full Service Module Pattern

```ruby
# app/services/accounts_service.rb
module AccountsService
  extend self
  
  # ============================================
  # Users
  # ============================================

  def list_users(organization_id)
    User.where(organization_id: organization_id)
  end

  def get_user(organization_id, id)
    User.find_by(id: id, organization_id: organization_id)
  end

  def get_user!(organization_id, id)
    User.find_by!(id: id, organization_id: organization_id)
  end

  def create_user(organization_id, attrs = {})
    user = User.new(attrs.merge(organization_id: organization_id))
    
    if user.save
      broadcast_user_created(user)
      { success: true, user: user }
    else
      { success: false, errors: user.errors }
    end
  end

  def update_user(user, attrs)
    if user.update(attrs)
      broadcast_user_updated(user)
      { success: true, user: user }
    else
      { success: false, errors: user.errors }
    end
  end

  def delete_user(user)
    user.destroy
    { success: true }
  end

  # ============================================
  # Authentication
  # ============================================

  def authenticate_user(email, password)
    user = User.find_by(email: email)

    if user&.authenticate(password)
      { success: true, user: user }
    else
      { success: false, error: :invalid_credentials }
    end
  end

  def generate_session_token(user)
    user.sessions.create!(token: SecureRandom.urlsafe_base64)
  end

  def get_user_by_session_token(token)
    session = Session.find_by(token: token)
    return unless session&.active?
    session.user
  end

  private

  def broadcast_user_created(user)
    Turbo::StreamsChannel.broadcast_prepend_to(
      "users",
      target: "users",
      partial: "users/user",
      locals: { user: user }
    )
  end

  def broadcast_user_updated(user)
    Turbo::StreamsChannel.broadcast_replace_to(
      "users",
      target: dom_id(user),
      partial: "users/user",
      locals: { user: user }
    )
  end
end
```

## Class-based Service Object

```ruby
# app/services/user_creator.rb
class UserCreator
  def initialize(organization_id, attrs = {})
    @organization_id = organization_id
    @attrs = attrs
  end

  def call
    @user = User.new(user_params)
    
    if @user.save
      send_welcome_email
      broadcast_creation
      Result.success(@user)
    else
      Result.failure(@user.errors)
    end
  end

  private

  def user_params
    @attrs.merge(organization_id: @organization_id)
  end

  def send_welcome_email
    UserMailer.welcome_email(@user).deliver_later
  end

  def broadcast_creation
    Turbo::StreamsChannel.broadcast_prepend_to(
      "users",
      target: "users",
      partial: "users/user",
      locals: { user: @user }
    )
  end
end

# Result object pattern
class Result
  attr_reader :data, :errors

  def self.success(data)
    new(success: true, data: data)
  end

  def self.failure(errors)
    new(success: false, errors: errors)
  end

  def initialize(success:, data: nil, errors: nil)
    @success = success
    @data = data
    @errors = errors
  end

  def success?
    @success
  end

  def failure?
    !@success
  end
end

# Usage
result = UserCreator.new(current_org.id, user_params).call
if result.success?
  redirect_to result.data
else
  render :new, status: :unprocessable_entity
end
```

## Query Object Pattern

```ruby
# app/queries/user_query.rb
class UserQuery
  def self.active
    new(User.active)
  end

  def initialize(relation = User.all)
    @relation = relation
  end

  def by_organization(org_id)
    @relation = @relation.where(organization_id: org_id)
    self
  end

  def with_posts
    @relation = @relation.includes(:posts)
    self
  end

  def recently_active(since: 1.week.ago)
    @relation = @relation.where("last_active_at > ?", since)
    self
  end

  def search(query)
    return self if query.blank?
    @relation = @relation.where("name ILIKE ? OR email ILIKE ?", "%#{query}%", "%#{query}%")
    self
  end

  def to_a
    @relation.to_a
  end

  def count
    @relation.count
  end
end

# Usage
users = UserQuery.active
                 .by_organization(current_org.id)
                 .with_posts
                 .recently_active
                 .search(params[:q])
                 .to_a
```

## Form Object Pattern

```ruby
# app/forms/registration_form.rb
class RegistrationForm
  include ActiveModel::Model
  include ActiveModel::Attributes

  attribute :email, :string
  attribute :password, :string
  attribute :password_confirmation, :string
  attribute :name, :string

  validates :email, presence: true, format: { with: URI::MailTo::EMAIL_REGEXP }
  validates :password, presence: true, length: { minimum: 8 }, confirmation: true
  validates :name, presence: true

  def save
    return false unless valid?

    ActiveRecord::Base.transaction do
      @user = User.create!(user_attributes)
      @user.create_profile!(profile_attributes)
      @user.send_welcome_email
    end
    
    true
  rescue ActiveRecord::RecordInvalid => e
    errors.add(:base, e.message)
    false
  end

  def user
    @user
  end

  private

  def user_attributes
    { email: email, password: password, name: name }
  end

  def profile_attributes
    { name: name }
  end
end

# Usage in controller
def create
  @form = RegistrationForm.new(registration_params)
  
  if @form.save
    redirect_to @form.user, notice: "Welcome!"
  else
    render :new, status: :unprocessable_entity
  end
end
```

## Policy/Authorization Object

```ruby
# app/policies/user_policy.rb
class UserPolicy
  def initialize(user, record)
    @user = user
    @record = record
  end

  def show?
    @record.organization_id == @user.organization_id
  end

  def update?
    @record.organization_id == @user.organization_id && 
      (@user.admin? || @record.id == @user.id)
  end

  def destroy?
    @user.admin? && @record.organization_id == @user.organization_id
  end

  class Scope
    def initialize(user, scope)
      @user = user
      @scope = scope
    end

    def resolve
      @scope.where(organization_id: @user.organization_id)
    end
  end
end

# Usage
def show
  @user = User.find(params[:id])
  authorize @user  # Uses UserPolicy#show?
  
  render json: @user
end

def index
  @users = policy_scope(User)  # Uses UserPolicy::Scope
  render json: @users
end
```

## Decorator/View Model Pattern

```ruby
# app/decorators/user_decorator.rb
class UserDecorator < SimpleDelegator
  def full_name
    "#{first_name} #{last_name}".strip
  end

  def member_since
    created_at.strftime("%B %Y")
  end

  def avatar_url(size: :medium)
    avatar.attached? ? avatar.variant(resize_to_limit: avatar_sizes[size]) : default_avatar
  end

  def status_badge
    content_tag :span, status, class: "badge badge-#{status}"
  end

  private

  def avatar_sizes
    { small: [50, 50], medium: [200, 200], large: [500, 500] }
  end
end

# Usage
def show
  @user = UserDecorator.new(User.find(params[:id]))
end
```

## Best Practices

### Keep Services Focused

```ruby
# Good: Single responsibility
class PasswordResetter
  def initialize(user)
    @user = user
  end

  def call
    generate_token
    send_email
    { success: true }
  end
end

# Bad: Too many responsibilities
class UserManager
  def create_user(attrs); end
  def reset_password(user); end
  def delete_account(user); end
  def export_data(user); end
end
```

### Return Consistent Results

```ruby
class UserCreator
  def call
    if user.save
      Result.success(user)
    else
      Result.failure(user.errors)
    end
  end
end

# Always check result type
case result
when Result::Success
  redirect_to result.data
when Result::Failure
  render :new, status: :unprocessable_entity
end
```

### Handle Transactions

```ruby
class OrderProcessor
  def initialize(order)
    @order = order
  end

  def call
    ActiveRecord::Base.transaction do
      charge_payment
      update_inventory
      mark_as_paid
    end
    Result.success(@order)
  rescue PaymentError => e
    Result.failure([e.message])
  end
end
```
