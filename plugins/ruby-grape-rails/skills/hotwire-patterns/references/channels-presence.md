# ActionCable and Turbo Streams Reference

## When to Use Turbo vs ActionCable

| Need | Use |
|------|-----|
| Interactive UI, server-rendered HTML | Turbo Streams |
| Custom binary protocol, gaming | ActionCable Channels |
| Mobile/desktop native client | ActionCable Channels |
| Bidirectional data sync (no HTML) | ActionCable Channels |
| Online user tracking | Custom solution with Redis or ActionCable |

**Default to Turbo Streams** for web apps. Use ActionCable when you need
non-HTML communication or native client support.

## ActionCable Channel Architecture

### Topic Routing

```ruby
# app/channels/application_cable/connection.rb
module ApplicationCable
  class Connection < ActionCable::Connection::Base
    identified_by :current_user

    def connect
      self.current_user = find_verified_user
    end

    private

    def find_verified_user
      if verified_user = User.find_by(id: cookies.encrypted[:user_id])
        verified_user
      else
        reject_unauthorized_connection
      end
    end
  end
end

# app/channels/room_channel.rb
class RoomChannel < ApplicationCable::Channel
  def subscribed
    stream_from "room:#{params[:room_id]}"
  end

  def unsubscribed
    # Any cleanup needed when channel is unsubscribed
  end

  def speak(data)
    Message.create!(
      content: data['message'],
      room_id: params[:room_id],
      user: current_user
    )
  end
end
```

### Authorization on Subscribe

```ruby
class RoomChannel < ApplicationCable::Channel
  def subscribed
    room = Room.find(params[:room_id])
    
    # Check authorization
    unless room.member?(current_user)
      reject
      return
    end
    
    stream_from "room:#{params[:room_id]}"
  end
end
```

### Broadcasting from Controller/Model

```ruby
# app/controllers/messages_controller.rb
class MessagesController < ApplicationController
  def create
    @message = current_user.messages.create!(message_params)
    
    # Broadcast to all subscribers
    ActionCable.server.broadcast(
      "room:#{@message.room_id}",
      {
        message: render_message(@message),
        user: @message.user.name
      }
    )
    
    head :ok
  end
  
  private
  
  def render_message(message)
    ApplicationController.render(
      partial: 'messages/message',
      locals: { message: message }
    )
  end
end

# Or use model callback
class Message < ApplicationRecord
  after_create_commit :broadcast_to_room
  
  private
  
  def broadcast_to_room
    ActionCable.server.broadcast(
      "room:#{room_id}",
      {
        message: MessagesController.render(partial: 'message', locals: { message: self }),
        user: user.name
      }
    )
  end
end
```

### Client-Side Patterns

```javascript
// app/javascript/channels/room_channel.js
import consumer from "./consumer"

const roomChannel = consumer.subscriptions.create({ channel: "RoomChannel", room_id: "123" }, {
  connected() {
    console.log("Connected to room")
  },

  disconnected() {
    console.log("Disconnected from room")
  },

  received(data) {
    // Called when there's incoming data on the websocket
    appendMessage(data.message, data.user)
  },

  speak: function(message) {
    return this.perform('speak', { message: message })
  }
})

// Send message
roomChannel.speak("Hello everyone!")
```

## Turbo Streams PubSub Pattern

### Model Broadcasting

```ruby
# app/models/message.rb
class Message < ApplicationRecord
  belongs_to :room
  
  # Broadcast to all subscribers of the room
  after_create_commit -> { broadcast_append_to room }
  after_update_commit -> { broadcast_replace_to room }
  after_destroy_commit -> { broadcast_remove_to room }
end

# app/models/room.rb
class Room < ApplicationRecord
  has_many :messages
  
  # Stream name for this room
  def to_param
    id
  end
end
```

### Controller Broadcasting

```ruby
# app/controllers/posts_controller.rb
class PostsController < ApplicationController
  def create
    @post = Post.create!(post_params)
    
    # Broadcast to all subscribers
    Turbo::StreamsChannel.broadcast_prepend_to(
      "posts",
      target: "posts",
      partial: "posts/post",
      locals: { post: @post }
    )
    
    respond_to do |format|
      format.html { redirect_to @post }
      format.turbo_stream  # Renders create.turbo_stream.erb
    end
  end
end
```

### View Subscription

```erb
<!-- app/views/rooms/show.html.erb -->
<%= turbo_stream_from @room %>

<div id="messages">
  <%= render @room.messages %>
</div>
```

### Turbo Stream Templates

```erb
<!-- app/views/messages/create.turbo_stream.erb -->
<%= turbo_stream.append "messages", partial: "message", locals: { message: @message } %>
<%= turbo_stream.update "message_count", @room.messages.count %>
<%= turbo_stream.scroll_into_view "message-#{@message.id}" %>
```

## Online Presence Tracking

### Simple Redis-Based Solution

```ruby
# app/models/concerns/online_trackable.rb
module OnlineTrackable
  extend ActiveSupport::Concern
  
  included do
    after_commit :track_online, on: :create
    after_commit :track_offline, on: :destroy
  end
  
  def track_online
    Redis.current.sadd("online:room:#{room_id}", user_id)
    Redis.current.expire("online:room:#{room_id}", 1.hour)
    broadcast_presence_change
  end
  
  def track_offline
    Redis.current.srem("online:room:#{room_id}", user_id)
    broadcast_presence_change
  end
  
  def broadcast_presence_change
    Turbo::StreamsChannel.broadcast_update_to(
      room,
      target: "online-users",
      html: render_online_users
    )
  end
  
  def render_online_users
    ApplicationController.render(
      partial: 'rooms/online_users',
      locals: { users: User.where(id: online_user_ids) }
    )
  end
  
  def online_user_ids
    Redis.current.smembers("online:room:#{room_id}")
  end
end

# app/models/user_session.rb
class UserSession < ApplicationRecord
  include OnlineTrackable
  
  belongs_to :user
  belongs_to :room
end
```

### With ActionCable

```ruby
# app/channels/presence_channel.rb
class PresenceChannel < ApplicationCable::Channel
  def subscribed
    stream_from "presence:#{params[:room_id]}"
    track_user_online
  end

  def unsubscribed
    track_user_offline
  end

  private

  def track_user_online
    PresenceTracker.track(
      room_id: params[:room_id],
      user_id: current_user.id,
      metadata: { name: current_user.name, joined_at: Time.current }
    )
    broadcast_presence_list
  end

  def track_user_offline
    PresenceTracker.untrack(params[:room_id], current_user.id)
    broadcast_presence_list
  end

  def broadcast_presence_list
    ActionCable.server.broadcast(
      "presence:#{params[:room_id]}",
      {
        users: PresenceTracker.list(params[:room_id])
      }
    )
  end
end

# app/services/presence_tracker.rb
class PresenceTracker
  def self.track(room_id:, user_id:, metadata:)
    Redis.current.hset("presence:#{room_id}", user_id, metadata.to_json)
    Redis.current.expire("presence:#{room_id}", 2.hours)
  end

  def self.untrack(room_id, user_id)
    Redis.current.hdel("presence:#{room_id}", user_id)
  end

  def self.list(room_id)
    Redis.current.hgetall("presence:#{room_id}").transform_values do |v|
      JSON.parse(v, symbolize_names: true)
    end
  end
end
```

## Navigation with Turbo

### Drive Navigation

```erb
<!-- Links are automatically handled by Turbo Drive -->
<%= link_to "Users", users_path %>
<%= link_to "Settings", settings_path, data: { turbo: true } %>
```

### Turbo Frames

```erb
<!-- Frame navigation updates only the frame -->
<%= turbo_frame_tag "user_form" do %>
  <%= render "form", user: @user %>
<% end %>

<!-- Link targets a specific frame -->
<%= link_to "Edit", edit_user_path(@user), data: { turbo_frame: "user_form" } %>
```

### Turbo Streams for Navigation

```ruby
# app/controllers/sessions_controller.rb
def create
  if user = User.authenticate(params[:email], params[:password])
    session[:user_id] = user.id
    
    respond_to do |format|
      format.html { redirect_to dashboard_path }
      format.turbo_stream do
        # Redirect via Turbo Stream
        render turbo_stream: turbo_stream.action(:redirect, dashboard_path)
      end
    end
  else
    flash.now[:alert] = "Invalid credentials"
    render :new, status: :unprocessable_entity
  end
end
```

## Anti-patterns

| Wrong | Right |
|-------|-------|
| ActionCable for HTML UI updates | Use Turbo Streams |
| No auth in channel subscription | Always verify user in `subscribed` |
| Broadcasting from views | Broadcast from models or controllers |
| No error handling in channel | Handle errors gracefully |
| Long-running operations in channel | Use Sidekiq for heavy work |

## Scalability Notes

- Turbo Streams work best for server-rendered HTML updates
- ActionCable can handle thousands of connections per server
- Use Redis adapter for ActionCable in production
- Consider using AnyCable for higher scalability
- Cache broadcasted partials when possible
