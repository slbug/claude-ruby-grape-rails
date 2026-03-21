# Android

```kotlin
// android/app/build.gradle
dependencies {
    implementation 'dev.hotwire:hotwire-native-android:1.2.5'
}
```

```kotlin
// android/app/src/main/java/com/example/app/MainActivity.kt
package com.example.app

import dev.hotwire.navigation.activities.HotwireActivity

class MainActivity : HotwireActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Configuration loaded from navigator
    }
}
```
