# Native Screens

## Native Screens

When the web isn't enough, use fully native screens:

```json
// path-configuration.json
{
  "patterns": ["/camera/native", "/map/fullscreen"],
  "properties": {
    "presentation": "native"
  }
}
```

### iOS Native Screen

```swift
// ios/App/NativeScreens/CameraViewController.swift
import AVFoundation
import UIKit

class CameraViewController: UIViewController {
    var captureSession: AVCaptureSession?
    var photoOutput: AVCapturePhotoOutput?
    
    var onPhotoCaptured: ((UIImage) -> Void)?
    
    override func viewDidLoad() {
        super.viewDidLoad()
        setupCamera()
    }
    
    private func setupCamera() {
        captureSession = AVCaptureSession()
        
        guard let device = AVCaptureDevice.default(for: .video),
              let input = try? AVCaptureDeviceInput(device: device),
              captureSession?.canAddInput(input) == true else {
            return
        }
        
        captureSession?.addInput(input)
        
        photoOutput = AVCapturePhotoOutput()
        if captureSession?.canAddOutput(photoOutput!) == true {
            captureSession?.addOutput(photoOutput!)
        }
        
        let previewLayer = AVCaptureVideoPreviewLayer(session: captureSession!)
        previewLayer.frame = view.bounds
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
        
        captureSession?.startRunning()
    }
    
    @objc func capturePhoto() {
        let settings = AVCapturePhotoSettings()
        photoOutput?.capturePhoto(with: settings, delegate: self)
    }
}

extension CameraViewController: AVCapturePhotoCaptureDelegate {
    func photoOutput(_ output: AVCapturePhotoOutput, 
                     didFinishProcessingPhoto photo: AVCapturePhoto, 
                     error: Error?) {
        guard let imageData = photo.fileDataRepresentation(),
              let image = UIImage(data: imageData) else { return }
        
        onPhotoCaptured?(image)
        dismiss(animated: true)
    }
}
```

### Android Native Screen

```kotlin
// android/app/src/main/java/com/example/app/native/CameraActivity.kt
package com.example.app.native

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class CameraActivity : AppCompatActivity() {
    
    companion object {
        const val EXTRA_PHOTO_PATH = "photo_path"
        
        fun newIntent(activity: Activity): Intent {
            return Intent(activity, CameraActivity::class.java)
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Camera setup using CameraX
    }
}
```
