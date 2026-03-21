# Testing

## Testing

### Web Testing

```ruby
# spec/system/native_app_spec.rb
require 'rails_helper'

RSpec.describe 'Native App', type: :system do
  before do
    driven_by :selenium, using: :headless_chrome
  end
  
  it 'loads in native app context' do
    visit '/'
    
    # Check for native app user agent
    expect(page).to have_selector('[data-native="true"]')
  end
  
  it 'renders bridge components' do
    visit '/profile/edit'
    
    expect(page).to have_selector('[data-controller="bridge--datepicker"]')
  end
end
```

### Native Testing

#### iOS (XCTest)

```swift
// ios/AppTests/HotwireNativeTests.swift
import XCTest
@testable import App

class HotwireNativeTests: XCTestCase {
    func testPathConfigurationLoading() {
        let config = PathConfiguration(sources: [
            .file(Bundle.main.url(forResource: "path-configuration", withExtension: "json")!)
        ])
        
        let rule = config.rules.first { rule in
            rule.patterns.contains("/sign_in")
        }
        
        XCTAssertNotNil(rule)
        XCTAssertEqual(rule?.properties["context"], "modal")
    }
    
    func testBridgeComponentRegistration() {
        let delegate = BridgeComponentDelegate(components: [DatepickerComponent.self])
        
        XCTAssertTrue(delegate.componentTypes.contains { $0 == DatepickerComponent.self })
    }
}
```

#### Android (JUnit)

```kotlin
// android/app/src/test/java/com/example/app/PathConfigurationTest.kt
package com.example.app

import org.junit.Test
import org.junit.Assert.*

class PathConfigurationTest {
    @Test
    fun testPathConfigurationLoading() {
        val config = PathConfiguration(
            sources = listOf(
                PathConfiguration.Source.File(
                    "path-configuration.json"
                )
            )
        )
        
        val rule = config.rules.find { it.patterns.contains("/sign_in") }
        
        assertNotNull(rule)
        assertEquals("modal", rule?.properties?.get("context"))
    }
}
```
