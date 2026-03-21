## Propshaft Asset Pipeline

Default in Rails 8, replaces Sprockets:

```ruby
# Gemfile
gem 'propshaft'
# Remove: gem 'sprockets-rails'
```

```javascript
// app/javascript/application.js
import '@hotwired/turbo-rails'
import './controllers'

// Import CSS
import '../stylesheets/application.css'
```

```css
/* app/assets/stylesheets/application.css */
@import 'tailwindcss';

/* Propshaft handles digests automatically */
.logo {
  background-image: url('logo.png');  /* -> logo-[digest].png */
}
```

### Propshaft vs Sprockets

| Feature | Propshaft | Sprockets |
|---------|-----------|-----------|
| Philosophy | Simple, fast | Full-featured |
| Compilation | External (esbuild, etc.) | Internal |
| CSS bundling | External | Internal |
| Source maps | External | Internal |
| Migration | Use for new Rails 8 apps | Keep for legacy |
