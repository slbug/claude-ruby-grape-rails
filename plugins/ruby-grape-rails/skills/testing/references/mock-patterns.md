# RSpec Mocks and Stubs Reference

## Setup

```ruby
# Mocking external services with doubles
RSpec.describe WeatherService do
  describe "#current_temperature" do
    let(:weather_api) { instance_double(WeatherAPI) }
    
    before do
      allow(WeatherAPI).to receive(:new).and_return(weather_api)
    end
    
    it "fetches temperature" do
      allow(weather_api).to receive(:get_temperature)
        .with("Chicago")
        .and_return({ temp: 72.0 })
      
      result = WeatherService.current_temperature("Chicago")
      expect(result).to eq(72.0)
    end
  end
end
```

## Usage

```ruby
RSpec.describe WeatherService do
  describe "#current_temperature" do
    let(:mock_api) { class_double(WeatherAPI) }
    
    before do
      stub_const("WeatherAPI", mock_api)
    end
    
    it "fetches temperature" do
      expect(mock_api).to receive(:get_temperature)
        .with("Chicago")
        .and_return({ temp: 72.0 })
      
      result = WeatherService.current_temperature("Chicago")
      expect(result).to eq(72.0)
    end
    
    # Stub for default behavior (not verified)
    it "uses stub for default" do
      allow(mock_api).to receive(:get_temperature).and_return({ temp: 70.0 })
      
      # Multiple calls use stub
      WeatherService.current_temperature("NYC")
      WeatherService.current_temperature("LA")
    end
    
    # Multiple calls with specific args
    it "allows multiple calls" do
      expect(mock_api).to receive(:get_temperature).exactly(3).times
        .and_return({ temp: 70.0 })
      
      3.times { WeatherService.current_temperature("City") }
    end
  end
end
```

## Allow vs Expect

| Method | Verification | Use When |
|--------|--------------|----------|
| `expect(...).to receive` | Verified | Testing specific call with specific args |
| `allow(...).to receive` | NOT verified | Default behavior, not testing the call |

## Async Tests with Mocks

```ruby
RSpec.describe "Async operations" do
  let(:mock_api) { instance_double(ApiClient) }
  
  it "handles concurrent calls" do
    allow(mock_api).to receive(:fetch).and_return({ data: "result" })
    
    threads = []
    results = []
    
    3.times do
      threads << Thread.new do
        results << Service.call(mock_api)
      end
    end
    
    threads.each(&:join)
    expect(results).to all(eq({ data: "result" }))
  end
  
  it "works with ThreadPool" do
    allow(ApiClient).to receive(:new).and_return(mock_api)
    allow(mock_api).to receive(:fetch).and_return({ data: "test" })
    
    pool = Concurrent::ThreadPoolExecutor.new(min_threads: 2, max_threads: 4)
    futures = 5.times.map do
      Concurrent::Future.execute(executor: pool) do
        Service.call
      end
    end
    
    results = futures.map(&:value)
    expect(results).to all(include(data: "test"))
  end
end
```

## Verifying Doubles

```ruby
# Verifying instance double - checks methods exist
RSpec.describe User do
  let(:user) { instance_double(User, name: "Jane", email: "jane@example.com") }
  
  it "uses verified double" do
    expect(user.name).to eq("Jane")
  end
end

# Verifying class double
RSpec.describe UserService do
  let(:user_class) { class_double(User).as_stubbed_const }
  
  it "finds users" do
    allow(user_class).to receive(:find).with(1).and_return(build(:user))
    
    UserService.find(1)
  end
end
```

## Method Stubs with Blocks

```ruby
RSpec.describe PaymentService do
  let(:stripe) { class_double(Stripe::Charge).as_stubbed_const }
  
  it "handles stripe errors" do
    allow(stripe).to receive(:create) do |params|
      if params[:amount] < 50
        raise Stripe::CardError.new("Amount too small", nil, nil)
      else
        { id: "ch_123", status: "succeeded" }
      end
    end
    
    expect { PaymentService.charge(25) }.to raise_error(PaymentError)
    expect(PaymentService.charge(100)).to eq("ch_123")
  end
end
```

## Anti-patterns

```ruby
RSpec.describe "Mocking" do
  # ❌ Mocking the database - never do this
  it "does not mock ActiveRecord" do
    allow(User).to receive(:find).and_return(mock_user)  # Bad!
    # Just use FactoryBot instead
  end
  
  # ✅ Use real records with FactoryBot
  it "uses real records" do
    user = create(:user)
    expect(User.find(user.id)).to eq(user)
  end
  
  # ❌ Over-specifying mocks
  it "is too specific" do
    expect(api).to receive(:call)
      .with("exact", "string", 123)  # Too brittle
  end
  
  # ✅ Use flexible matchers
  it "is flexible" do
    expect(api).to receive(:call)
      .with(anything(), include(:key), kind_of(Integer))
  end
  
  # ❌ Not verifying expectations
  it "might not call mock" do
    allow(api).to receive(:call)  # No expect!
    subject.do_something
    # Test passes even if api.call never happens
  end
  
  # ✅ Verify with expect
  it "verifies the call" do
    expect(api).to receive(:call)  # Will fail if not called
    subject.do_something
  end
end
```

## Shared Stub Configurations

```ruby
# spec/support/api_stubs.rb
module ApiStubs
  def stub_weather_api(temp: 72.0)
    weather = class_double(WeatherAPI).as_stubbed_const
    allow(weather).to receive(:get_temperature).and_return({ temp: temp })
    weather
  end
  
  def stub_stripe_payment(success: true, charge_id: "ch_123")
    stripe = class_double(Stripe::Charge).as_stubbed_const
    if success
      allow(stripe).to receive(:create).and_return({ id: charge_id, status: "succeeded" })
    else
      allow(stripe).to receive(:create).and_raise(Stripe::CardError.new("Declined", nil, nil))
    end
    stripe
  end
end

RSpec.configure do |config|
  config.include ApiStubs
end
```

## Partial Doubles (on real objects)

```ruby
RSpec.describe "Partial mocking" do
  let(:real_user) { create(:user) }
  
  it "stubs a method on real object" do
    allow(real_user).to receive(:admin?).and_return(true)
    expect(real_user.admin?).to be true
    # Original method restored after test
  end
  
  it "stubs only for specific args" do
    allow(real_user).to receive(:can_edit?).with(Post).and_return(true)
    allow(real_user).to receive(:can_edit?).with(Comment).and_return(false)
    
    expect(real_user.can_edit?(Post.new)).to be true
    expect(real_user.can_edit?(Comment.new)).to be false
  end
end
```

## Spy Pattern

```ruby
RSpec.describe "Spy pattern" do
  it "records method calls" do
    api_spy = spy("API")
    
    service = Service.new(api_spy)
    service.process
    
    expect(api_spy).to have_received(:fetch).with("data")
    expect(api_spy).to have_received(:save).once
  end
end
```
