---
name: rb:init
description: Initialize the Ruby/Rails/Grape plugin in a project. Installs auto-activation rules into CLAUDE.md for complexity detection, workflow routing, Iron Laws, and Ruby stack auto-loading.
argument-hint: "[--update]"
---

# Plugin Initialization

Install the Ruby/Rails/Grape behavioral instructions into the project `CLAUDE.md`.

## Usage

```bash
/rb:init
/rb:init --update
```

## Detect the Stack

Check the project before writing anything. Use Ruby for detection (avoids fragile shell pipelines):

```bash
# Detect Ruby version and stack dependencies
ruby ${CLAUDE_PLUGIN_ROOT}/scripts/detect-stack.rb

# Or inline detection (fallback):
ruby -e '
  gemfile = File.read("Gemfile") rescue ""
  lock = File.read("Gemfile.lock") rescue ""

  puts "Ruby: #{RUBY_VERSION}"
  puts "Rails: #{lock[/rails \(([^)]+)\)/, 1] || "?"}"
  puts "Grape: #{lock[/grape \(([^)]+)\)/, 1] || "?"}"
  puts "Sidekiq: #{lock[/sidekiq \(([^)]+)\)/, 1] || "?"}"
  puts "Redis: detected" if gemfile.match?(/gem.*redis/)
  puts "PostgreSQL: detected" if gemfile.match?(/gem.*pg/)
  puts "Sidekiq: detected" if gemfile.match?(/gem.*sidekiq/)
  puts "Hotwire: detected" if gemfile.match?(/gem.*hotwire-rails/)
  puts "Karafka: detected" if gemfile.match?(/gem.*karafka/)
  puts "Grape: detected" if gemfile.match?(/gem.*grape/)
'

# External tools (shell is fine here - simple commands)
command -v rtk &> /dev/null && echo "RTK: available"
command -v betterleaks &> /dev/null && echo "Betterleaks: available"
```

## Install Modes

- Fresh install: append a managed block to `CLAUDE.md`
- Update mode: replace the content between markers only

Managed block markers:

```markdown
<!-- RUBY-GRAPE-RAILS-PLUGIN:START -->
...
<!-- RUBY-GRAPE-RAILS-PLUGIN:END -->
```

## What Gets Installed

- workflow routing for `/rb:plan`, `/rb:work`, `/rb:review`, `/rb:verify`
- Ruby Iron Laws
- stack-aware auto-loading for Rails, Grape, Active Record, Sidekiq, security, and testing
- verification defaults for Zeitwerk, formatter, tests, and optional Brakeman

## Template

Use `references/injectable-template.md` as the injected source of truth.

## Conditional Sections

Include based on detected stack and installed tools:

- `{SIDEKIQ_SECTION}` — If Sidekiq detected
- `{HOTWIRE_SECTION}` — If Hotwire/Turbo detected
- `{KARAFKA_SECTION}` — If Karafka detected
- `{RTK_SECTION}` — If RTK installed (token optimization tool)
- `{BETTERLEAKS_SECTION}` — If Betterleaks installed (secrets scanning)

See `references/conditional-sections.md` for full content of each section.
