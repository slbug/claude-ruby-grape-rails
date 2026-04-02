# RSpec Patterns Reference

## Setup and Context

```ruby
# spec/spec_helper.rb
RSpec.configure do |config|
  config.include FactoryBot::Syntax::Methods
  
  # Database cleaning
  config.before(:suite) do
    DatabaseCleaner.strategy = :transaction
    DatabaseCleaner.clean_with(:truncation)
  end

  config.around(:each) do |example|
    DatabaseCleaner.cleaning do
      example.run
    end
  end
end

# spec/rails_helper.rb
require 'spec_helper'
require 'rspec/rails'

RSpec.configure do |config|
  config.fixture_paths = ["#{Rails.root}/spec/fixtures"]
  config.use_transactional_fixtures = true
  config.infer_spec_type_from_file_location!
  config.filter_rails_from_backtrace!
end
```

## Describe and Context Blocks

```ruby
RSpec.describe "Admin actions", type: :request do
  let(:user) { create(:user) }
  let(:admin) { create(:user, :admin) }
  
  before do
    sign_in(admin)
  end

  describe "DELETE #destroy" do
    context "when admin is authenticated" do
      it "can delete user" do
        delete user_path(user)
        expect(response).to redirect_to(users_path)
        expect(User).not_to exist(user.id)
      end
    end
    
    context "when not authenticated" do
      before { sign_out }
      
      it "redirects to login" do
        delete user_path(user)
        expect(response).to redirect_to(login_path)
      end
    end
  end
end
```

## Tags and Filtering

```ruby
RSpec.describe "Integration tests", integration: true do
  describe "slow operations", slow: true do
    it "performs slowly" do
      # Test code
    end
  end
  
  describe "quick operations" do
    it "is fast", timeout: 120 do
      # Test code
    end
  end
end

# Run only tagged tests:
# bundle exec rspec --tag integration
# bundle exec rspec --tag ~slow
```

## Matchers

```ruby
# Equality
expect(actual).to eq(expected)        # ==
expect(actual).to eql(expected)      # .eql?
expect(actual).to equal(expected)    # same object

# Pattern matching (with RSpec 3.10+)
expect(actual).to match({ id: be_a(Integer), name: "Jane" })

# Messages (using rspec-wait gem)
expect { subject }.to send_message(MessageClass, :deliver)

# Negation
expect(user).not_to be_admin

# Exceptions
expect { 1 / 0 }.to raise_error(ZeroDivisionError)
expect { User.find(-1) }.to raise_error(ActiveRecord::RecordNotFound, /couldn't find/)

# Numeric with delta
expect(1.15).to be_within(0.1).of(1.1)

# Collections
expect([1, 2, 3]).to include(2)
expect({ a: 1, b: 2 }).to include(a: 1)

# Predicate matchers
expect(user).to be_valid
expect(user).to be_a_kind_of(User)
```

## Model Spec Helper

```ruby
# spec/support/model_helpers.rb
module ModelHelpers
  def errors_on(object, attribute)
    object.errors[attribute].join(', ')
  end
end

RSpec.configure do |config|
  config.include ModelHelpers, type: :model
end

# spec/models/user_spec.rb
RSpec.describe User, type: :model do
  describe "validations" do
    it "validates presence of email" do
      user = build(:user, email: nil)
      expect(user).not_to be_valid
      expect(errors_on(user, :email)).to include("can't be blank")
    end
  end
end
```

## Request Spec Helper

```ruby
# spec/support/request_helpers.rb
module RequestHelpers
  def sign_in(user)
    post login_path, params: { email: user.email, password: user.password }
  end
  
  def sign_out
    delete logout_path
  end
  
  def json_response
    JSON.parse(response.body)
  end
end

RSpec.configure do |config|
  config.include RequestHelpers, type: :request
  
  config.before(:each, type: :request) do
    host! 'localhost'
  end
end

# spec/requests/users_spec.rb
RSpec.describe "Users", type: :request do
  describe "GET /users" do
    it "returns users list" do
      get users_path
      expect(response).to have_http_status(:ok)
    end
  end
end
```

## CI Partitioning

Split tests across CI machines for faster runs:

```yaml
# Example workflow file in your app repo: .github/workflows/test.yml
strategy:
  matrix:
    ci_node_index: [0, 1, 2, 3]
    ci_node_total: [4]

- name: Run tests
  env:
    CI_NODE_INDEX: ${{ matrix.ci_node_index }}
    CI_NODE_TOTAL: ${{ matrix.ci_node_total }}
  run: |
    bundle exec rspec --profile 10 \
      --format progress \
      $(bundle exec rspec --dry-run --format json | \
        ruby -rjson -e "puts JSON.parse(STDIN.read)['examples'].map { |e| e['id'] }.sort_by(&:hash).select.with_index { |_, i| i % ENV['CI_NODE_TOTAL'].to_i == ENV['CI_NODE_INDEX'].to_i }")
```

## Seed-Based Flaky Test Debugging

RSpec runs tests in random order by default. When tests fail
intermittently, re-run with the specific seed:

```bash
# Failed run shows seed
bundle exec rspec  # "Randomized with seed 401472"

# Reproduce exact order
bundle exec rspec --seed 401472
```

If tests pass with `--seed` but fail randomly, you have
state leakage between tests. Check:

- Shared class variables or global state
- Missing database cleaning between tests
- Time zone or locale changes not reset

## Running Test Subsets

```bash
bundle exec rspec spec/models/user_spec.rb        # Single file
bundle exec rspec spec/models/user_spec.rb:42      # Single test at line
bundle exec rspec spec/models/                   # Directory
bundle exec rspec --tag integration              # Tagged tests
bundle exec rspec --tag ~slow                  # Exclude tagged
bundle exec rspec --only-failures                # Re-run failures only
bundle exec rspec --next-failure                 # Run until failure
```

## Filtering Verbose Test Output

When E2E test output (Capybara, Playwright) is too
noisy, filter for signal:

```bash
# Filter for summary only
bundle exec rspec spec/features/user_flow_spec.rb --format documentation 2>&1 | \
  grep -E '(example|Finished|failure|✓|✗|success|Failed|Error|PASS|FAIL|examples)'

# Capybara feature tests: filter results
bundle exec rspec spec/features --format progress 2>&1 | \
  tail -20
```

**Rule**: When running E2E tests, always pipe through a filter
to extract pass/fail signal. Raw output is too noisy to read.
