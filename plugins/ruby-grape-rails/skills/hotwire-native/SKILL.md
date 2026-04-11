---
name: hotwire-native
description: Hotwire Native patterns for building native iOS/Android mobile apps using Turbo Native. Load when developing native mobile apps that reuse Rails views. Covers path configuration, bridge components, native screens, and web-to-native communication.
user-invocable: false
effort: medium
paths:
  - "app/views/**/*.erb"
  - app/javascript/**
  - app/components/**
  - app/channels/**
  - "**/app/views/**/*.erb"
  - "**/app/components/**"
  - ios/**
  - android/**
  - native/**
---
# Hotwire Native

## Iron Laws

1. **Reuse web screens first** - Build in HTML/CSS before reaching for native screens.
2. **Use path configuration** to control routing behavior declaratively.
3. **Bridge components for native upgrade** - Use Strada when the web isn't enough.
4. **Keep native and web in sync** - Version bridge components together.
5. **Test on real devices** - Simulators don't catch all native behaviors.
6. **Handle offline gracefully** - Native apps expect resilience.

## Overview

Hotwire Native wraps your web app in a native shell (iOS/Android), providing:

- Native navigation transitions between web screens
- Access to native SDKs and APIs via Bridge Components
- Push notifications, camera, location, and other native features
- App store distribution with web-first updates
- Fallback to native screens when needed

```
┌─────────────────────────────────────────────────────────────┐
│                    HOTWIRE NATIVE ARCHITECTURE              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐         ┌──────────────┐                 │
│  │   iOS App    │         │ Android App  │                 │
│  │  (Swift/UIKit)│        │  (Kotlin)    │                 │
│  └──────┬───────┘         └──────┬───────┘                 │
│         │                        │                          │
│         └────────┬───────────────┘                          │
│                  │                                          │
│         ┌────────▼────────┐                                 │
│         │  Turbo Native   │                                 │
│         │    Navigator    │                                 │
│         └────────┬────────┘                                 │
│                  │                                          │
│         ┌────────▼────────┐                                 │
│         │   WebView       │                                 │
│         │ (WKWebView/     │                                 │
│         │  WebChromeClient)│                                │
│         └────────┬────────┘                                 │
│                  │                                          │
│                  │  HTTP/WebSocket                         │
│                  │                                          │
│         ┌────────▼────────┐                                 │
│         │   Rails App     │                                 │
│         │  (Turbo/        │                                 │
│         │   Stimulus)     │                                 │
│         └─────────────────┘                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Installation

See detailed setup guides:

- [iOS Setup](references/ios-setup.md) — Xcode, CocoaPods, Swift configuration
- [Android Setup](references/android-setup.md) — Gradle, Kotlin, manifest configuration

## Core Concepts

### Path Configuration

Declarative routing rules control native vs web behavior:

```json
{
  "rules": [
    {
      "patterns": ["/sign_in", "/sign_up"],
      "properties": { "context": "modal" }
    },
    {
      "patterns": ["/settings/*"],
      "properties": { "context": "default" }
    }
  ]
}
```

See [Path Configuration](references/path-configuration.md) for full reference.

### Bridge Components (Strada)

Bridge components expose native SDKs to your web app:

```javascript
// Web side
import { BridgeComponent } from "@hotwired/strada"

export default class extends BridgeComponent {
  static component = "datepicker"
  
  openDatePicker() {
    this.send("open", { minDate: "2024-01-01" })
  }
}
```

See [Bridge Components](references/bridge-components.md) for component authoring.

## Detailed Guides

- [iOS Setup](references/ios-setup.md)
- [Android Setup](references/android-setup.md)
- [Path Configuration](references/path-configuration.md)
- [Bridge Components](references/bridge-components.md)
- [Common Components](references/common-components.md) — Camera, Location, Share, Alerts
- [Native Screens](references/native-screens.md) — When to use native UI
- [Push Notifications](references/push-notifications.md)
- [Offline Support](references/offline-support.md)
- [Testing](references/testing.md)
- [Best Practices](references/best-practices.md)
- [Anti-patterns](references/anti-patterns.md)

## Key Decisions

| Decision | Recommendation |
|----------|----------------|
| Web vs Native screen | Start with web; use native for platform-specific features (camera, GPS) |
| Bridge component needed? | Use when HTML5 API insufficient (background location, push notifications) |
| Path config patterns | Use wildcards sparingly; prefer explicit paths |
| Testing strategy | Unit test web; integration test native flows on real devices |

## See Also

- [Hotwire Patterns](../hotwire-patterns/SKILL.md) — Turbo Frames, Streams, Stimulus
- [Rails Contexts](../rails-contexts/SKILL.md) — Controllers, routing, contexts
- [Request State Audit](../request-state-audit/SKILL.md) — Audit state management
