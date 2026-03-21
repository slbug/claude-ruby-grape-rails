## Rails 8 Async Queries

```ruby
# Automatic async loading in controllers
class ProductsController < ApplicationController
  def index
    @products = Product.active.load_async
    @categories = Category.all.load_async
    # Both queries run in parallel
  end
end

# Explicit async with handling
products = Product.where(active: true).load_async
# ... do other work ...
products.to_a  # Wait for result here

# Use when:
# - Multiple independent queries
# - I/O wait time > query execution time
# - In controller actions, not background jobs
```
