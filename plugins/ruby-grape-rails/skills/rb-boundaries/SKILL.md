---
name: rb:boundaries
description: Analyze context and service boundaries in Rails applications. Detect coupling, misplaced logic, and violations of architectural boundaries. Use when refactoring services, splitting monoliths, or reviewing layer interactions.
argument-hint: "[path|service|context] [--focus controllers|models|services|grape]"
---

# Rails Boundary Analysis

Analyze coupling and boundary violations between Rails layers.

## Boundary Layers

```
┌─────────────────────────────────────┐
│  Controllers / Grape Endpoints      │  ← HTTP transport only
├─────────────────────────────────────┤
│  Services / Commands / Interactors  │  ← Business logic
├─────────────────────────────────────┤
│  Queries / Policies / Forms         │  ← Specialized concerns
├─────────────────────────────────────┤
│  Models                             │  ← Data + simple scopes
├─────────────────────────────────────┤
│  Jobs / Mailers / External APIs     │  ← Async / external
└─────────────────────────────────────┘
```

## Iron Laws

1. **Controllers do not contain business logic** - Only HTTP concerns
2. **Models do not call external services directly** - Use callbacks carefully
3. **Services do not depend on request context** - Pass data explicitly
4. **Jobs receive IDs, not records** - JSON-safe args only
5. **Cross-context calls go through explicit APIs** - No deep coupling

## Violations to Detect

```ruby
# ❌ Business logic in controller
def create
  if params[:type] == 'premium'
    # This belongs in a service
    apply_discount
    create_invoice
    send_welcome_email
  end
end

# ❌ External call in model callback
class Order < ApplicationRecord
  after_create :notify_warehouse # Dangerous - use job
end

# ❌ Service depending on request
class CheckoutService
  def initialize(session) # Too coupled
    @session = session
  end
end

# ❌ Cross-context dependency
class InvoiceService
  def generate
    OrderService.new.process # Deep coupling - use events/API
  end
end
```

## Packwerk & Modular Monoliths

For larger applications, enforce boundaries with [Packwerk](https://github.com/Shopify/packwerk):

```yaml
# packwerk.yml
exclude:
  - "vendor/**"
  - "spec/**"
  - "test/**"

# package.yml in packs/ directory
enforce_dependencies: true
enforce_privacy: true
dependencies:
  - packs/orders
  - packs/users
```

**Recommendation**: For monoliths >50K LOC, use Packwerk. For smaller apps, follow the layer boundaries above.

## Analysis Output

```
## Boundary Analysis: app/services/

### Violations
- OrdersController#create: 40 lines business logic → extract CheckoutService
- Order: after_create calls Stripe directly → use OrderCreatedJob
- InvoiceService depends on OrderService → introduce event bus

### Recommendations
- Move billing logic from controllers to Billing::ChargeService
- Replace model callbacks with explicit service calls
- Add policy layer for authorization (currently in controllers)
- Consider Packwerk for packs/billing/ isolation
```
