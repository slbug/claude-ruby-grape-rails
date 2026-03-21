# Common Bridge Components

## Common Bridge Components

### Camera

```javascript
// app/javascript/controllers/bridge/camera_controller.js
import { BridgeComponent } from '@hotwired/strada'

export default class extends BridgeComponent {
  static component = 'camera'
  
  capture() {
    this.send('capture', {
      quality: 0.8,
      allowEditing: true,
      source: 'camera' // or 'library' or 'both'
    })
  }
  
  photoCaptured({ data }) {
    // data.imageData - base64 encoded image
    // data.metadata - EXIF data
    this.dispatch('camera:photo-captured', { 
      detail: data,
      bubbles: true 
    })
  }
}
```

### Location

```javascript
// app/javascript/controllers/bridge/location_controller.js
import { BridgeComponent } from '@hotwired/strada'

export default class extends BridgeComponent {
  static component = 'location'
  
  getCurrentPosition() {
    this.send('getCurrentPosition', {
      accuracy: 'high', // 'high', 'medium', 'low'
      timeout: 10000
    })
  }
  
  watchPosition() {
    this.send('watchPosition', {
      accuracy: 'high',
      distanceFilter: 10 // meters
    })
  }
  
  stopWatching() {
    this.send('stopWatching')
  }
  
  positionReceived({ data }) {
    // data.latitude, data.longitude, data.accuracy
    this.dispatch('location:updated', { detail: data })
  }
  
  errorReceived({ data }) {
    // data.code, data.message
    this.dispatch('location:error', { detail: data })
  }
}
```

### Share

```javascript
// app/javascript/controllers/bridge/share_controller.js
import { BridgeComponent } from '@hotwired/strada'

export default class extends BridgeComponent {
  static component = 'share'
  
  share(event) {
    const { title, text, url } = event.params
    
    this.send('share', {
      title: title || document.title,
      text: text || '',
      url: url || window.location.href
    })
  }
  
  shareCompleted({ data }) {
    this.dispatch('share:completed', { detail: data })
  }
}
```

```erb
<button data-controller="bridge--share"
        data-action="click->bridge--share#share"
        data-bridge--share-title-param="Check this out!"
        data-bridge--share-text-param="<%= post.summary %>">
  Share
</button>
```

### Native Alerts

```javascript
// app/javascript/controllers/bridge/alert_controller.js
import { BridgeComponent } from '@hotwired/strada'

export default class extends BridgeComponent {
  static component = 'alert'
  
  confirm(event) {
    const { title, message, confirmText, cancelText } = event.params
    
    this.send('confirm', {
      title,
      message,
      confirmText: confirmText || 'OK',
      cancelText: cancelText || 'Cancel'
    })
  }
  
  alert(event) {
    const { title, message, buttonText } = event.params
    
    this.send('alert', {
      title,
      message,
      buttonText: buttonText || 'OK'
    })
  }
  
  actionSheet(event) {
    const { title, options } = event.params
    
    this.send('actionSheet', {
      title,
      options: options.map((opt, index) => ({
        title: opt,
        index: index,
        destructive: opt.destructive || false
      }))
    })
  }
  
  dialogCompleted({ data }) {
    // data.buttonIndex - which button was tapped
    // data.cancelled - true if dismissed
    this.dispatch('alert:completed', { detail: data })
  }
}
```
