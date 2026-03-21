# Offline Support

## Offline Support

```javascript
// app/javascript/controllers/bridge/offline_controller.js
import { BridgeComponent } from '@hotwired/strada'

export default class extends BridgeComponent {
  static component = 'offline'
  
  connect() {
    super.connect()
    this.send('checkConnectivity')
    
    // Listen for offline events
    window.addEventListener('offline', this.handleOffline.bind(this))
    window.addEventListener('online', this.handleOnline.bind(this))
  }
  
  handleOffline() {
    this.send('offline')
    this.showOfflineNotice()
  }
  
  handleOnline() {
    this.send('online')
    this.hideOfflineNotice()
  }
  
  showOfflineNotice() {
    // Show native offline banner
    this.send('showNotice', {
      message: 'You are offline. Changes will sync when connection is restored.',
      style: 'warning'
    })
  }
  
  hideOfflineNotice() {
    this.send('hideNotice')
  }
  
  connectivityChanged({ data }) {
    if (!data.isConnected) {
      this.enableOfflineMode()
    }
  }
  
  enableOfflineMode() {
    // Store form submissions in localStorage
    // Queue API requests
    // Show offline UI
  }
}
```
