# Testing Patterns with Modern Ruby

## RSpec with Dependency Injection

```ruby
RSpec.describe CreateOrder do
  subject(:service) { described_class.new(deps) }
  
  let(:deps) do
    {
      inventory_checker: instance_double(InventoryChecker),
      payment_processor: instance_double(PaymentProcessor),
      notifier: instance_double(OrderNotifier)
    }
  end
  
  describe '#call' do
    context 'when inventory is available' do
      before do
        allow(deps[:inventory_checker]).to receive(:check!)
      end
      
      it 'creates an order' do
        expect { service.call(user:, items:) }
          .to change(Order, :count).by(1)
      end
    end
    
    context 'when inventory is insufficient' do
      before do
        allow(deps[:inventory_checker])
          .to receive(:check!)
          .and_raise(InsufficientInventory)
      end
      
      it 'returns a failure result' do
        result = service.call(user:, items:)
        expect(result).to be_failure
      end
    end
  end
end
```
