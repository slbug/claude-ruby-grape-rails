# Rails System/Integration Testing Reference

## System Tests with Capybara

```ruby
# spec/system/user_flow_spec.rb
require 'rails_helper'

RSpec.describe "User Flow", type: :system do
  before do
    driven_by(:selenium_chrome_headless)
  end
  
  it "user can interact with counter" do
    visit "/counter"
    expect(page).to have_content("Count: 0")
    
    click_button "Increment"
    
    expect(page).to have_content("Count: 1")
  end
end
```

## Form Testing

```ruby
# spec/system/user_registration_spec.rb
RSpec.describe "User Registration", type: :system do
  it "validates form on change (Turbo Stream)" do
    visit "/users/new"
    
    # Validation on change with Turbo
    fill_in "Email", with: "invalid"
    
    # Wait for Turbo Stream update
    expect(page).to have_content("must be a valid email")
    
    # Fill correctly and submit
    fill_in "Email", with: "valid@example.com"
    fill_in "Name", with: "Jane"
    click_button "Sign Up"
    
    expect(page).to have_current_path("/users")
    expect(page).to have_content("User created successfully")
  end
end
```

## Async Operations (CRITICAL)

```ruby
# spec/system/dashboard_spec.rb
RSpec.describe "Dashboard", type: :system do
  it "loads data asynchronously (Turbo Frame)" do
    visit "/dashboard"
    expect(page).to have_content("Loading...")
    
    # Wait for Turbo Frame to load
    within_frame("dashboard_data") do
      expect(page).to have_content("Dashboard Data")
    end
    
    # Or wait for element to appear
    expect(page).to have_content("Dashboard Data", wait: 5)
  end
  
  it "handles Stimulus controllers" do
    visit "/search"
    
    fill_in "Query", with: "test"
    
    # Wait for Stimulus debounced search
    sleep 0.5
    
    expect(page).to have_selector(".search-result", count: 3)
  end
end
```

## ActionCable/PubSub Testing

```ruby
# spec/channels/chat_channel_spec.rb
RSpec.describe ChatChannel, type: :channel do
  let(:user) { create(:user) }
  
  before do
    stub_connection current_user: user
  end
  
  it "subscribes to room" do
    subscribe(room: "room1")
    
    expect(subscription).to be_confirmed
    expect(subscription.streams).to include("chat:room1")
  end
  
  it "broadcasts messages" do
    subscribe(room: "room1")
    
    # Simulate receiving broadcast
    ActionCable.server.broadcast("chat:room1", { message: "Hello!" })
    
    expect(transmissions.last).to eq({ "message" => "Hello!" })
  end
end

# System test for real-time updates
RSpec.describe "Chat", type: :system do
  it "updates on broadcast from other user", js: true do
    user1 = create(:user)
    user2 = create(:user)
    
    # User 1 visits chat
    visit "/chat/room1"
    sign_in(user1)
    
    expect(page).to have_content("Chat Room")
    
    # User 2 sends message via different session
    using_session(:user2) do
      visit "/chat/room1"
      sign_in(user2)
      fill_in "Message", with: "Hello from User 2!"
      click_button "Send"
    end
    
    # User 1 sees the message
    expect(page).to have_content("Hello from User 2!")
  end
end
```

## File Uploads

```ruby
# spec/system/upload_spec.rb
RSpec.describe "File Upload", type: :system do
  it "uploads file with Active Storage" do
    visit "/upload"
    
    attach_file "Avatar", Rails.root.join("spec/fixtures/photo.jpg")
    
    # Wait for direct upload to complete
    expect(page).to have_content("100%", wait: 10)
    
    click_button "Upload"
    
    expect(page).to have_content("Upload complete")
    expect(User.last.avatar).to be_attached
  end
end
```

## Navigation Testing

```ruby
# spec/system/navigation_spec.rb
RSpec.describe "Navigation", type: :system do
  it "uses Turbo Drive for page navigation" do
    visit "/posts"
    
    # Click link - page changes via Turbo Drive
    click_link "Next Page"
    
    expect(page).to have_current_path("/posts?page=2")
    
    # Verify Turbo cached the previous page
    page.go_back
    expect(page).to have_current_path("/posts")
  end
  
  it "handles Turbo Stream redirects" do
    visit "/login"
    
    fill_in "Email", with: "user@example.com"
    fill_in "Password", with: "password"
    click_button "Sign In"
    
    # Redirect after successful login
    expect(page).to have_current_path("/dashboard")
  end
  
  it "uses Turbo Frames for partial updates" do
    visit "/posts"
    
    # Click within Turbo Frame
    within_frame("post_1") do
      click_link "Edit"
    end
    
    # Only the frame updates, not full page
    expect(page).to have_selector("form[action*='post_1']")
  end
end
```

## Common Mistakes

```ruby
RSpec.describe "Testing mistakes", type: :system do
  # ❌ Not waiting for async operations
  it "fails without waiting" do
    visit "/dashboard"
    
    # Async data not loaded yet!
    expect(page).to have_content("Data")  # May fail
  end
  
  # ✅ Use Capybara's wait/retry
  it "waits for content" do
    visit "/dashboard"
    
    # Capybara waits up to 2 seconds (configurable)
    expect(page).to have_content("Data", wait: 5)
  end
  
  # ❌ Testing implementation not behavior
  it "checks internal state" do
    visit "/counter"
    click_button "Increment"
    
    # Bad: checking internal variable
    expect(page.execute_script("return window.counterValue")).to eq(1)
  end
  
  # ✅ Test user-visible behavior
  it "checks visible result" do
    visit "/counter"
    click_button "Increment"
    
    # Good: checking what user sees
    expect(page).to have_content("Count: 1")
  end
  
  # ❌ Not handling JavaScript errors
  it "might miss JS errors" do
    visit "/page"
    # If JS errors occur, test might still pass
  end
  
  # ✅ Enable JS error reporting
  it "reports JS errors", js: true do
    expect {
      visit "/page"
    }.not_to raise_error
    
    # Check console for errors
    errors = page.driver.browser.logs.get(:browser)
    expect(errors.select { |e| e.level == "SEVERE" }).to be_empty
  end
end
```

## Testing Turbo Streams

```ruby
# spec/requests/turbo_streams_spec.rb
RSpec.describe "Turbo Streams", type: :request do
  it "sends turbo stream response" do
    post posts_path, params: { post: attributes_for(:post) }, as: :turbo_stream
    
    expect(response.content_type).to eq("text/vnd.turbo-stream.html; charset=utf-8")
    expect(response.body).to include("<turbo-stream action=")
  end
end

# spec/system/turbo_stream_spec.rb
RSpec.describe "Turbo Streams", type: :system do
  it "appends new post to list" do
    visit "/posts"
    
    fill_in "Title", with: "New Post"
    click_button "Create Post"
    
    # Turbo Stream appends without page reload
    expect(page).to have_content("New Post")
    expect(page).not_to have_current_path("/posts/new")
  end
end
```

## Testing Stimulus Controllers

```ruby
# spec/system/stimulus_spec.rb
RSpec.describe "Stimulus Controllers", type: :system do
  it "toggles visibility" do
    visit "/page"
    
    # Initially hidden
    expect(page).not_to have_selector("#details.visible")
    
    # Click toggle button
    click_button "Show Details"
    
    # Stimulus controller made it visible
    expect(page).to have_selector("#details.visible")
  end
  
  it "handles debounced input" do
    visit "/search"
    
    fill_in "Search", with: "ruby"
    
    # Wait for debounce (Stimulus controller typically 300ms)
    sleep 0.4
    
    # Results appeared via fetch/XHR
    expect(page).to have_selector(".search-result", minimum: 1)
  end
end
```

## Performance Testing

```ruby
RSpec.describe "Performance", type: :system do
  it "loads within acceptable time" do
    start_time = Time.current
    
    visit "/dashboard"
    
    expect(page).to have_content("Dashboard", wait: 2)
    
    load_time = Time.current - start_time
    expect(load_time).to be < 2.0
  end
  
  it "handles many Turbo Streams efficiently", js: true do
    visit "/feed"
    
    # Trigger many updates
    10.times { |i| ActionCable.server.broadcast("feed", { item: "Item #{i}" }) }
    
    # All should appear without page becoming unresponsive
    10.times do |i|
      expect(page).to have_content("Item #{i}")
    end
  end
end
```
