# Bridge Components (Strada)

## Bridge Components (Strada)

Bridge components enable bidirectional communication between web and native:

```
Web (Stimulus) <---> Bridge Component <---> Native (iOS/Android)
```

### Creating a Bridge Component

#### Web Side (Stimulus)

```javascript
// app/javascript/controllers/bridge/datepicker_controller.js
import { BridgeComponent } from '@hotwired/strada'

export default class extends BridgeComponent {
  static component = 'datepicker'
  static targets = ['input']
  
  connect() {
    super.connect()
    this.send('connect', { format: 'yyyy-MM-dd' })
  }
  
  open() {
    this.send('open', { 
      value: this.inputTarget.value,
      minDate: this.inputTarget.dataset.minDate,
      maxDate: this.inputTarget.dataset.maxDate
    })
  }
  
  // Receive message from native
  dateSelected({ data }) {
    this.inputTarget.value = data.value
    this.inputTarget.dispatchEvent(new Event('change'))
  }
  
  disconnect() {
    this.send('disconnect')
  }
}
```

```erb
<!-- app/views/events/_form.html.erb -->
<div data-controller="bridge--datepicker" 
     data-bridge--datepicker-value="<%= event.date %>">
  <%= f.text_field :date, 
                   data: { 
                     bridge__datepicker_target: 'input',
                     min_date: Date.today,
                     max_date: 1.year.from_now
                   },
                   class: 'native-datepicker' %>
  
  <button data-action="click->bridge--datepicker#open">
    Select Date
  </button>
</div>
```

#### iOS Side (Swift)

```swift
// ios/App/BridgeComponents/DatepickerComponent.swift
import HotwireNative
import UIKit

class DatepickerComponent: BridgeComponent {
    override var name: String { "datepicker" }
    
    private var format: String = "yyyy-MM-dd"
    private var datePicker: UIDatePicker?
    
    override func onReceive(message: Message) {
        switch message.event {
        case "connect":
            handleConnect(message: message)
        case "open":
            handleOpen(message: message)
        case "disconnect":
            handleDisconnect()
        default:
            break
        }
    }
    
    private func handleConnect(message: Message) {
        if let data = message.data {
            format = data["format"] as? String ?? format
        }
    }
    
    private func handleOpen(message: Message) {
        guard let data = message.data else { return }
        
        let datePicker = UIDatePicker()
        datePicker.datePickerMode = .date
        
        if #available(iOS 14, *) {
            datePicker.preferredDatePickerStyle = .inline
        }
        
        // Set initial value
        if let value = data["value"] as? String,
           let date = parseDate(value) {
            datePicker.date = date
        }
        
        // Set constraints
        if let minDate = data["minDate"] as? String {
            datePicker.minimumDate = parseDate(minDate)
        }
        
        if let maxDate = data["maxDate"] as? String {
            datePicker.maximumDate = parseDate(maxDate)
        }
        
        datePicker.addTarget(self, 
                            action: #selector(dateChanged),
                            for: .valueChanged)
        
        self.datePicker = datePicker
        
        // Present picker
        let vc = UIViewController()
        vc.view = datePicker
        vc.preferredContentSize = datePicker.frame.size
        
        delegate?.present(vc, animated: true)
    }
    
    @objc private func dateChanged() {
        guard let datePicker = datePicker else { return }
        
        let formatter = DateFormatter()
        formatter.dateFormat = format
        let value = formatter.string(from: datePicker.date)
        
        reply(to: "dateSelected", with: ["value": value])
    }
    
    private func handleDisconnect() {
        datePicker = nil
    }
    
    private func parseDate(_ string: String) -> Date? {
        let formatter = DateFormatter()
        formatter.dateFormat = format
        return formatter.date(from: string)
    }
}
```

#### Android Side (Kotlin)

```kotlin
// android/app/src/main/java/com/example/app/bridge/DatepickerComponent.kt
package com.example.app.bridge

import android.app.DatePickerDialog
import dev.hotwire.bridge.BridgeComponent
import dev.hotwire.bridge.BridgeDelegate
import dev.hotwire.bridge.Message
import java.text.SimpleDateFormat
import java.util.*

class DatepickerComponent(
    name: String,
    private val delegate: BridgeDelegate
) : BridgeComponent(name, delegate) {
    
    private var format = "yyyy-MM-dd"
    private val calendar = Calendar.getInstance()
    
    override fun onReceive(message: Message) {
        when (message.event) {
            "connect" -> handleConnect(message)
            "open" -> handleOpen(message)
            "disconnect" -> handleDisconnect()
        }
    }
    
    private fun handleConnect(message: Message) {
        message.data?.let {
            format = it.optString("format", format)
        }
    }
    
    private fun handleOpen(message: Message) {
        val data = message.data ?: return
        
        // Parse initial value
        data.optString("value").takeIf { it.isNotEmpty() }?.let {
            parseDate(it)?.let { date ->
                calendar.time = date
            }
        }
        
        val dialog = DatePickerDialog(
            delegate.fragment.requireContext(),
            { _, year, month, day ->
                calendar.set(year, month, day)
                val value = formatDate(calendar.time)
                replyTo("dateSelected", mapOf("value" to value))
            },
            calendar.get(Calendar.YEAR),
            calendar.get(Calendar.MONTH),
            calendar.get(Calendar.DAY_OF_MONTH)
        )
        
        // Set constraints
        data.optString("minDate").takeIf { it.isNotEmpty() }?.let {
            parseDate(it)?.let { date ->
                dialog.datePicker.minDate = date.time
            }
        }
        
        data.optString("maxDate").takeIf { it.isNotEmpty() }?.let {
            parseDate(it)?.let { date ->
                dialog.datePicker.maxDate = date.time
            }
        }
        
        dialog.show()
    }
    
    private fun handleDisconnect() {
        // Cleanup
    }
    
    private fun parseDate(string: String): Date? {
        return try {
            SimpleDateFormat(format, Locale.getDefault()).parse(string)
        } catch (e: Exception) {
            null
        }
    }
    
    private fun formatDate(date: Date): String {
        return SimpleDateFormat(format, Locale.getDefault()).format(date)
    }
}
```

### Registering Bridge Components

#### iOS

```swift
// ios/App/SceneDelegate.swift
import HotwireNative
import UIKit

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    
    private lazy var navigator = Navigator(
        pathConfiguration: pathConfiguration,
        delegates: [
            BridgeComponentDelegate(
                components: [
                    DatepickerComponent.self,
                    CameraComponent.self,
                    LocationComponent.self,
                    ShareComponent.self
                ]
            )
        ]
    )
    
    private var pathConfiguration: PathConfiguration {
        let configuration = PathConfiguration(sources: [
            .server(URL(string: "https://myapp.com/native/path-configuration")!)
        ])
        return configuration
    }
    
    func scene(_ scene: UIScene, 
               willConnectTo session: UISceneSession, 
               options connectionOptions: UIScene.ConnectionOptions) {
        guard let windowScene = scene as? UIWindowScene else { return }
        
        window = UIWindow(windowScene: windowScene)
        window?.rootViewController = navigator.rootViewController
        window?.makeKeyAndVisible()
        
        navigator.route(URL(string: "https://myapp.com")!)
    }
}
```

#### Android

```kotlin
// android/app/src/main/java/com/example/app/MainActivity.kt
package com.example.app

import dev.hotwire.bridge.BridgeComponentFactory
import dev.hotwire.navigation.activities.HotwireActivity
import dev.hotwire.navigation.navigator.NavigatorConfiguration

class MainActivity : HotwireActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        val configuration = NavigatorConfiguration(
            startLocation = "https://myapp.com",
            pathConfigurationLocation = PathConfiguration.Location(
                remoteUrl = "https://myapp.com/native/path-configuration"
            )
        )
        
        val bridgeComponents = listOf(
            BridgeComponentFactory("datepicker", ::DatepickerComponent),
            BridgeComponentFactory("camera", ::CameraComponent),
            BridgeComponentFactory("location", ::LocationComponent),
            BridgeComponentFactory("share", ::ShareComponent)
        )
        
        navigator.registerBridgeComponents(bridgeComponents)
        navigator.route(configuration.startLocation)
    }
}
```
