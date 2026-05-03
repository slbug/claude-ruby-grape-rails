# iOS

Set up via Xcode project + CocoaPods. Initialize the Podfile, add
`pod 'HotwireNative', '~> 1.2'` to it, then install:

```bash
cd ios
pod init
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
