# Anti-patterns

## Anti-patterns

```javascript
// ❌ Don't assume bridge is always available
connect() {
  this.send('connect')  // Crashes if not in native app
}

// ✅ Check bridge availability
connect() {
  if (this.bridgeConnected) {
    this.send('connect')
  }
}

// ❌ Don't send large data over bridge
this.send('upload', { imageData: hugeBase64String })  // Too slow!

// ✅ Upload via HTTP, send URL over bridge
uploadToServer(imageData).then(url => {
  this.send('showImage', { url: url })
})

// ❌ Don't block native UI
this.send('process')  // Long-running operation

// ✅ Use async pattern
this.send('startProcess')
// ... native shows spinner ...
// Later: replyTo('processComplete', result)
```
