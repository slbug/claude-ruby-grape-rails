## Testing

```ruby
# System tests with Rails 8 defaults
class OrderSystemTest < ActionDispatch::SystemTestCase
  driven_by :selenium, using: :headless_chrome
  
  test "user creates an order" do
    user = users(:one)
    product = products(:book)
    
    sign_in user
    visit product_path(product)
    click_on "Add to Cart"
    click_on "Checkout"
    fill_in "Credit Card", with: "4242424242424242"
    click_on "Place Order"
    
    assert_text "Order confirmed!"
    assert_equal 1, user.orders.count
  end
end

# Request specs
class OrdersControllerTest < ActionDispatch::IntegrationTest
  test "creates order with valid params" do
    user = users(:one)
    
    assert_difference -> { Order.count } do
      post orders_path, params: {
        order: {
          items: [{ product_id: products(:book).id, quantity: 2 }]
        }
      }, headers: auth_headers(user)
    end
    
    assert_response :created
  end
end

# Parallel testing (built-in)
# test/test_helper.rb
class ActiveSupport::TestCase
  parallelize(workers: :number_of_processors)
end
```
