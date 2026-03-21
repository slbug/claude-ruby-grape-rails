# FactoryBot Patterns Reference

## Setup

```ruby
# Gemfile
group :test do
  gem 'factory_bot_rails'
  gem 'faker'
end

# spec/support/factory_bot.rb
RSpec.configure do |config|
  config.include FactoryBot::Syntax::Methods
end

# spec/factories/users.rb
FactoryBot.define do
  factory :user do
    name { Faker::Name.name }
    email { Faker::Internet.email }
    password { "password123" }
    
    # Traits
    trait :admin do
      role { :admin }
    end
    
    trait :verified do
      verified_at { Time.current }
    end
    
    # Sequence for uniqueness
    sequence(:username) { |n| "user#{n}" }
  end
end
```

## Key Patterns

```ruby
# BUILD by default (no DB hit)
user = build(:user)

# CREATE only when needed
user = create(:user)

# CREATE with traits
admin = create(:user, :admin)
verified_admin = create(:user, :admin, :verified)

# Build and save manually
user = build(:user)
user.save!  # or user.save

# Associations - use build in factory, create when needed
# spec/factories/posts.rb
FactoryBot.define do
  factory :post do
    title { "Test Post" }
    body { Faker::Lorem.paragraph }
    association :author, factory: :user  # Creates user when post is created
    
    # Or use transient for more control
    transient do
      author_name { nil }
    end
    
    after(:build) do |post, evaluator|
      if evaluator.author_name
        post.author ||= build(:user, name: evaluator.author_name)
      end
    end
  end
end

# Sequences for uniqueness
FactoryBot.define do
  factory :product do
    sequence(:sku) { |n| "SKU-#{n.to_s.rjust(6, '0')}" }
    sequence(:name) { |n| "Product #{n}" }
  end
end
```

## Updating Factories for Required Validations

When a model adds validations with `presence: true`, update ALL factories
BEFORE running tests to prevent cascade failures:

1. Find all factories that build the affected model
2. Add the new required fields with sensible defaults
3. Then run the test suite

```ruby
# Model added validations:
# validates :currency_code, presence: true
# validates :area_unit, presence: true

# Update factory FIRST:
FactoryBot.define do
  factory :deal do
    title { "Deal Title" }
    currency_code { :USD }          # NEW required field
    area_unit { :square_feet }       # NEW required field
    
    trait :metric do
      currency_code { :EUR }
      area_unit { :square_meters }
    end
  end
end
```

Skipping this step causes 20+ test failures that all have the same
root cause (missing factory field) but look like unrelated failures.

## Build Strategies

```ruby
# build - instantiate but don't save
user = build(:user)  # #<User id: nil, name: "...">

# build_stubbed - fake id, skip validation, don't save
user = build_stubbed(:user)  # #<User id: 1234, name: "...">
# Use for view tests where you just need an object with an id

# create - save to database
user = create(:user)  # #<User id: 1, name: "...">

# create_list - multiple records
users = create_list(:user, 5)

# build_list - multiple unsaved
users = build_list(:user, 5)

# attributes_for - hash of attributes
attrs = attributes_for(:user)  # { name: "...", email: "..." }

# attributes_for with associations (shallow)
attrs = attributes_for(:post)  # { title: "...", user_id: nil }
```

## Associations and Callbacks

```ruby
FactoryBot.define do
  factory :order do
    customer
    
    after(:build) do |order, evaluator|
      # Build hook - runs before :create too
      order.order_number ||= "ORD-#{SecureRandom.hex(4).upcase}"
    end
    
    after(:create) do |order, evaluator|
      # Create hook - only runs on create
      create(:shipping_address, order: order) unless order.shipping_address
    end
    
    # Nested factories with different associations
    factory :order_with_items do
      transient do
        items_count { 3 }
      end
      
      after(:create) do |order, evaluator|
        create_list(:order_item, evaluator.items_count, order: order)
      end
    end
  end
end

# Usage
order = create(:order_with_items, items_count: 5)
expect(order.items.count).to eq(5)
```

## Faker Integration

```ruby
FactoryBot.define do
  factory :user do
    name { Faker::Name.name }
    email { Faker::Internet.email }
    phone { Faker::PhoneNumber.cell_phone }
    bio { Faker::Lorem.paragraph(sentence_count: 3) }
    
    # Conditional faker
    company_name { Faker::Company.name if Faker::Boolean.boolean }
    
    # Unique within constraints
    sequence(:slug) { |n| "#{Faker::Internet.slug}-#{n}" }
  end
  
  factory :address do
    street { Faker::Address.street_address }
    city { Faker::Address.city }
    state { Faker::Address.state_abbr }
    zip { Faker::Address.zip }
    country { "US" }
  end
end
```

## Dynamic Attributes

```ruby
FactoryBot.define do
  factory :product do
    name { "Widget" }
    price { 10.00 }
    
    # Dynamic based on other attributes
    sale_price { price * 0.8 }
    
    # Dynamic with transient attributes
    transient do
      discount_percent { 0 }
    end
    
    sale_price { price * (1 - discount_percent / 100.0) }
  end
end

# Usage
product = create(:product, price: 100.00, discount_percent: 20)
expect(product.sale_price).to eq(80.00)
```

## Anti-patterns

```ruby
# ❌ create() in factory definitions
trait :with_profile do
  after(:build) do |user|
    create(:profile, user: user)  # Creates record even on build()!
  end
end

# ✅ Use build() in factories, let test decide when to create
trait :with_profile do
  after(:build) do |user|
    user.profile ||= build(:profile, user: user)
  end
end

# ❌ Hardcoded unique values
insert(:user, email: "test@example.com")  # Will fail on second run!

# ✅ Use sequences
insert(:user)  # Uses sequence for email

# ❌ Unnecessary persistence
it "validates name" do
  user = create(:user, name: nil)  # Creates then validates
  expect(user).not_to be_valid
end

# ✅ Just build for validations
it "validates name" do
  user = build(:user, name: nil)
  expect(user).not_to be_valid
end
```

## Sidekiq Testing with Factories

```ruby
# spec/support/sidekiq.rb
require 'sidekiq/testing'

RSpec.configure do |config|
  config.before do
    Sidekiq::Job.clear_all
  end
end

# spec/jobs/welcome_email_job_spec.rb
RSpec.describe WelcomeEmailJob, type: :job do
  let(:user) { create(:user) }
  
  describe "#perform" do
    it "enqueues job on user creation" do
      expect {
        UserService.create(attributes_for(:user))
      }.to change(WelcomeEmailJob.jobs, :size).by(1)
    end
    
    it "processes job correctly" do
      WelcomeEmailJob.perform_inline(user.id)
      
      expect(ActionMailer::Base.deliveries.last.to).to include(user.email)
    end
  end
end
```

## Testing Factory Validity

```ruby
# spec/factories_spec.rb
RSpec.describe "Factories" do
  FactoryBot.factories.each do |factory|
    context "with factory :#{factory.name}" do
      it "is valid" do
        record = build(factory.name)
        
        if record.respond_to?(:valid?)
          expect(record).to be_valid, -> { record.errors.full_messages.join(',') }
        end
      end
      
      it "can be created" do
        expect { create(factory.name) }.not_to raise_error
      end
    end
  end
end
```
