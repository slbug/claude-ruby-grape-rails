# iOS

```bash
# Using Xcode project
cd ios
pod init

# Add to Podfile
pod 'HotwireNative', '~> 1.2'

pod install
```

```swift
// ios/App/AppDelegate.swift
import HotwireNative
import UIKit

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(_ application: UIApplication, 
                     didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?) -> Bool {
        return true
    }
}
```
