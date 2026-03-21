# Push Notifications

## Push Notifications

### iOS Setup

```swift
// ios/App/AppDelegate.swift
import UIKit
import UserNotifications

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    
    func application(_ application: UIApplication, 
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        registerForPushNotifications()
        return true
    }
    
    func registerForPushNotifications() {
        UNUserNotificationCenter.current()
            .requestAuthorization(options: [.alert, .sound, .badge]) { granted, _ in
                if granted {
                    DispatchQueue.main.async {
                        UIApplication.shared.registerForRemoteNotifications()
                    }
                }
            }
    }
    
    func application(_ application: UIApplication, 
                     didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data) {
        let token = deviceToken.map { String(format: "%02.2hhx", $0) }.joined()
        // Send token to Rails backend
        sendTokenToBackend(token)
    }
    
    private func sendTokenToBackend(_ token: String) {
        // POST /api/devices with device token
    }
}
```

### Rails Backend

```ruby
# app/models/device.rb
class Device < ApplicationRecord
  belongs_to :user
  
  enum platform: { ios: 0, android: 1 }
  
  validates :token, presence: true, uniqueness: true
end
```

```ruby
# app/services/push_notification_service.rb
class PushNotificationService
  def self.send_to_user(user:, title:, body:, data: {})
    user.devices.find_each do |device|
      send_to_device(device, title: title, body: body, data: data)
    end
  end
  
  def self.send_to_device(device, title:, body:, data: {})
    case device.platform
    when 'ios'
      send_apns(device.token, title: title, body: body, data: data)
    when 'android'
      send_fcm(device.token, title: title, body: body, data: data)
    end
  end
  
  private
  
  def self.send_apns(token, title:, body:, data:)
    # Use apnotic or similar gem
    notification = Apnotic::Notification.new(token)
    notification.alert = { title: title, body: body }
    notification.custom_payload = data
    
    # Send via APNS
  end
  
  def self.send_fcm(token, title:, body:, data:)
    # Use fcm gem
    fcm = FCM.new(ENV['FCM_SERVER_KEY'])
    fcm.send(
      [token],
      notification: { title: title, body: body },
      data: data
    )
  end
end
```
