## Testing Hotwire

```ruby
# test/system/posts_test.rb
class PostsTest < ApplicationSystemTestCase
  test "creates post with turbo stream" do
    visit posts_url
    
    click_on "New Post"
    fill_in "Title", with: "My First Post"
    fill_in "Body", with: "Hello World"
    
    assert_difference -> { Post.count } do
      click_on "Create Post"
      
      # Wait for turbo stream to update
      assert_selector "#posts article", text: "My First Post"
    end
  end
  
  test "live updates via turbo stream broadcast" do
    visit post_url(posts(:one))
    
    # Simulate another user creating a comment
    Comment.create!(post: posts(:one), body: "New comment!")
    
    # Wait for broadcast to appear
    assert_selector "#comments", text: "New comment!"
  end
end
```

```ruby
# test/controllers/posts_controller_test.rb
class PostsControllerTest < ActionDispatch::IntegrationTest
  test "creates post and returns turbo stream" do
    post posts_url, params: {
      post: { title: "Test", body: "Body" }
    }, as: :turbo_stream
    
    assert_response :success
    assert_turbo_stream action: :prepend, target: "posts"
  end
end
```
