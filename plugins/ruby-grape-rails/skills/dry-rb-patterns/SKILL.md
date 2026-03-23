---
name: dry-rb-patterns
description: Functional programming patterns with dry-rb gems for Rails. Covers validation, types, structs, monads, and transactions.
user-invocable: false
effort: medium
---
# dry-rb Patterns

Functional programming tools for Ruby with dry-rb.

## Overview

dry-rb provides type-safe, composable tools for Ruby:

| Gem | Purpose | Use Case |
|-----|---------|----------|
| dry-validation | Schema validation | Params, forms, contracts |
| dry-types | Type constraints | Attribute typing |
| dry-struct | Immutable value objects | Domain models |
| dry-monads | Result/Maybe monads | Service composition |
| dry-transaction | Business transaction DSL | Operation pipelines |
| dry-system | Dependency injection | Component architecture |

## dry-validation

Schema-based validation for params and forms.

### Basic Contract

```ruby
require 'dry-validation'

class UserContract < Dry::Validation::Contract
  params do
    required(:name).filled(:string, min_size?: 3)
    required(:email).filled(:string, format?: /@/)
    optional(:age).maybe(:integer, gteq?: 0)
  end
  
  rule(:email) do
    key.failure('has invalid format') unless value.include?('@')
  end
end

# Usage
contract = UserContract.new
result = contract.call(name: 'John', email: 'john@example.com')

if result.success?
  result.to_h  # { name: 'John', email: 'john@example.com' }
else
  result.errors.to_h  # { email: ['has invalid format'] }
end
```

### Rails Integration

```ruby
# app/contracts/application_contract.rb
class ApplicationContract < Dry::Validation::Contract
  config.messages.backend = :i18n
  config.messages.load_paths << Rails.root.join('config/locales/dry_validation.en.yml')
end

# app/controllers/users_controller.rb
class UsersController < ApplicationController
  def create
    contract = UserContract.new
    result = contract.call(user_params)
    
    if result.success?
      User.create!(result.to_h)
    else
      render json: { errors: result.errors.to_h }, status: :unprocessable_entity
    end
  end
end
```

### Validation Rules

```ruby
class OrderContract < Dry::Validation::Contract
  params do
    required(:items).array(:hash) do
      required(:product_id).filled(:integer)
      required(:quantity).filled(:integer, gt?: 0)
    end
    required(:shipping_address).hash do
      required(:street).filled(:string)
      required(:city).filled(:string)
    end
  end
  
  # Custom rule
  rule(:items) do
    if value.empty?
      key.failure('must have at least one item')
    end
  end
  
  # Cross-field validation
  rule(:shipping_address) do
    unless valid_zip?(value[:zip])
      key(:shipping_address)[:zip].failure('is invalid')
    end
  end
end
```

## dry-types

Type constraints for Ruby.

### Basic Types

```ruby
require 'dry-types'

module Types
  include Dry.Types()
  
  # Coercible types
  CoercibleString = Types::Coercible::String
  CoercibleInteger = Types::Coercible::Integer
  CoercibleFloat = Types::Coercible::Float
  
  # Strict types (no coercion)
  StrictString = Types::Strict::String
  StrictInteger = Types::Strict::Integer
  
  # Optional types
  MaybeString = Types::String.optional
  MaybeInteger = Types::Integer.optional
  
  # Custom types
  Email = Types::String.constrained(format: /@/)
  Phone = Types::String.constrained(format: /\A\+?\d{10,15}\z/)
end

# Usage
Types::CoercibleInteger['123']      # => 123
Types::StrictInteger['123']         # => Dry::Types::ConstraintError
Types::Email['invalid']             # => Dry::Types::ConstraintError
Types::Email['test@example.com']    # => "test@example.com"
```

### Rails Attributes

```ruby
# app/models/user.rb
class User < ApplicationRecord
  attribute :age, Types::Coercible::Integer
  attribute :tags, Types::Array.of(Types::String)
  attribute :settings, Types::Hash.default({}.freeze)
  
  validates :email, format: { with: /@/ }
end
```

## dry-struct

Immutable value objects.

### Basic Struct

```ruby
require 'dry-struct'

module Types
  include Dry.Types()
end

class Address < Dry::Struct
  attribute :street, Types::String
  attribute :city, Types::String
  attribute :zip, Types::String
  attribute? :country, Types::String.default('USA')
end

class User < Dry::Struct
  attribute :id, Types::Integer
  attribute :name, Types::String
  attribute :email, Types::String
  attribute :address, Address
end

# Usage
user = User.new(
  id: 1,
  name: 'John',
  email: 'john@example.com',
  address: {
    street: '123 Main St',
    city: 'Boston',
    zip: '02101'
  }
)

user.name        # => "John"
user.address.city # => "Boston"

# Immutable - this raises an error
user.name = 'Jane'  # NoMethodError
```

### Sum Types

```ruby
class PaymentMethod < Dry::Struct
  attribute :type, Types::String.enum('credit_card', 'paypal', 'bank_transfer')
  
  # Union type - different attributes based on type
  attribute :details, Types::Hash
end

# Or use inheritance
class CreditCard < Dry::Struct
  attribute :number, Types::String
  attribute :expiry, Types::String
  attribute :cvv, Types::String
end

class PayPal < Dry::Struct
  attribute :email, Types::String
end

Payment = CreditCard | PayPal
```

## dry-monads

Result and Maybe monads for composable operations.

### Result Monad (Either)

```ruby
require 'dry-monads'
require 'dry-monads/do'

class CreateUser
  include Dry::Monads[:result, :do]
  
  def call(params)
    # Each step must return Success or Failure
    values = yield validate(params)
    user = yield create_user(values)
    yield send_welcome_email(user)
    
    Success(user)
  end
  
  private
  
  def validate(params)
    contract = UserContract.new
    result = contract.call(params)
    
    if result.success?
      Success(result.to_h)
    else
      Failure(result.errors.to_h)
    end
  end
  
  def create_user(values)
    user = User.new(values)
    
    if user.save
      Success(user)
    else
      Failure(user.errors.to_h)
    end
  rescue ActiveRecord::RecordNotUnique
    Failure(email: ['has already been taken'])
  end
  
  def send_welcome_email(user)
    UserMailer.welcome(user).deliver_later
    Success(user)
  rescue => e
    Failure(email: ['could not be sent'])
  end
end

# Usage
result = CreateUser.new.call(name: 'John', email: 'john@example.com')

case result
when Dry::Monads::Success
  puts "Created: #{result.value!}"
when Dry::Monads::Failure
  puts "Failed: #{result.failure}"
end

# Or bind to chain operations
CreateUser.new
  .call(params)
  .bind { |user| CreateProfile.new.call(user) }
  .bind { |user| SendNotification.new.call(user) }
  .or { |error| LogError.new.call(error) }
```

### Maybe Monad (Optional)

```ruby
include Dry::Monads[:maybe]

# Safe navigation
def find_user(id)
  Maybe(User.find_by(id: id))
end

user = find_user(123)
  .bind { |u| Maybe(u.profile) }
  .bind { |p| Maybe(p.address) }
  .value_or('No address found')

# Alternative with fmap
Maybe(User.find_by(id: 123))
  .fmap { |u| u.name.upcase }
  .value_or('Unknown')
```

## dry-transaction

Business transaction DSL.

### Transaction Definition

```ruby
require 'dry-transaction'

class CreateOrder
  include Dry::Transaction
  
  step :validate
  step :calculate_totals
  step :process_payment
  step :create_order
  step :send_confirmation
  
  def validate(input)
    contract = OrderContract.new
    result = contract.call(input)
    
    if result.success?
      Success(result.to_h)
    else
      Failure(result.errors.to_h)
    end
  end
  
  def calculate_totals(input)
    items = input[:items]
    subtotal = items.sum { |i| i[:price] * i[:quantity] }
    tax = subtotal * 0.08
    total = subtotal + tax
    
    Success(input.merge(subtotal: subtotal, tax: tax, total: total))
  end
  
  def process_payment(input)
    result = PaymentGateway.charge(input[:total], input[:payment_method])
    
    if result.success?
      Success(input.merge(payment_id: result.id))
    else
      Failure(payment: [result.error_message])
    end
  end
  
  def create_order(input)
    order = Order.create!(input.slice(:items, :total, :payment_id))
    Success(order)
  rescue ActiveRecord::RecordInvalid => e
    Failure(order: [e.message])
  end
  
  def send_confirmation(order)
    OrderMailer.confirmation(order).deliver_later
    Success(order)
  end
end

# Usage
CreateOrder.new.call(params) do |result|
  result.success do |order|
    redirect_to order_path(order)
  end
  
  result.failure do |errors|
    render json: { errors: errors }, status: :unprocessable_entity
  end
end
```

## Iron Laws

1. **Validate at boundaries** - Use contracts for params/forms
2. **Fail fast** - Return errors immediately, don't continue
3. **Use monads for composition** - Chain operations cleanly
4. **Prefer immutability** - Structs over mutable state
5. **Type at system edges** - Input/output, not everywhere
6. **Keep transactions pure** - No side effects in steps

## Integration with Rails

### Controller Pattern

```ruby
class ApplicationController < ActionController::API
  include Dry::Monads[:result]
  
  private
  
  def handle_result(result, success_status: :ok)
    case result
    when Dry::Monads::Success
      render json: result.value!, status: success_status
    when Dry::Monads::Failure
      render json: { errors: result.failure }, status: :unprocessable_entity
    end
  end
end

class UsersController < ApplicationController
  def create
    result = CreateUser.new.call(user_params)
    handle_result(result, success_status: :created)
  end
end
```

### Service Object Pattern

```ruby
# app/services/application_service.rb
class ApplicationService
  include Dry::Monads[:result, :do]
  
  def self.call(*args)
    new.call(*args)
  end
end

# app/services/create_user.rb
class CreateUser < ApplicationService
  def call(params)
    values = yield validate(params)
    user = yield persist(values)
    yield notify(user)
    
    Success(user)
  end
  
  private
  
  def validate(params)
    # ...
  end
  
  def persist(values)
    # ...
  end
  
  def notify(user)
    # ...
  end
end
```

## Testing

See: [references/testing.md](references/testing.md) — Testing patterns for contracts, monads, and structs
