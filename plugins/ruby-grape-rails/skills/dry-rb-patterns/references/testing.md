# Testing dry-rb Components

Testing patterns for dry-validation, dry-monads, and other dry-rb gems.

## Testing Monads

```ruby
RSpec.describe CreateUser do
  subject(:service) { described_class.new }
  
  describe '#call' do
    context 'with valid params' do
      let(:params) { { name: 'John', email: 'john@example.com' } }
      
      it 'returns Success' do
        result = service.call(params)
        expect(result).to be_a(Dry::Monads::Success)
        expect(result.value!).to be_a(User)
      end
    end
    
    context 'with invalid params' do
      let(:params) { { name: '', email: 'invalid' } }
      
      it 'returns Failure' do
        result = service.call(params)
        expect(result).to be_a(Dry::Monads::Failure)
        expect(result.failure).to include(:email)
      end
    end
  end
end
```

## Testing Contracts

```ruby
RSpec.describe UserContract do
  subject(:contract) { described_class.new }
  
  describe '#call' do
    context 'with valid attributes' do
      let(:params) { { name: 'John', email: 'john@example.com' } }
      
      it 'returns Success' do
        result = contract.call(params)
        expect(result).to be_success
      end
    end
    
    context 'with invalid attributes' do
      let(:params) { { name: '', email: 'invalid' } }
      
      it 'returns Failure with errors' do
        result = contract.call(params)
        expect(result).to be_failure
        expect(result.errors[:email]).to include('has invalid format')
      end
    end
  end
end
```

## Testing Structs

```ruby
RSpec.describe Address do
  describe '#new' do
    it 'creates immutable struct' do
      address = Address.new(
        street: '123 Main St',
        city: 'Boston',
        zip: '02101'
      )
      
      expect(address.street).to eq('123 Main St')
      expect { address.street = '456 Oak Ave' }.to raise_error(NoMethodError)
    end
  end
end
```
