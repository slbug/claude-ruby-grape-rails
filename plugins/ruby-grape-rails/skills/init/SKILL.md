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

Check the project before writing anything.

Detection rules:

1. **Always run** `ruby ${CLAUDE_PLUGIN_ROOT}/scripts/detect-stack.rb` first.
2. **Prefer exact `*_VERSION` values** from that script when writing the managed-block header.
3. Use plain `detected` only as a last resort when a direct gem is present but no resolved lockfile version is available.
4. **Never** use broad substring regexes like `/rails \(([^)]+)\)/` against raw `Gemfile.lock`; they can falsely match gems such as `rubocop-rails`.

Use Ruby for detection (avoids fragile shell pipelines):

```bash
# Detect Ruby version and stack dependencies
ruby ${CLAUDE_PLUGIN_ROOT}/scripts/detect-stack.rb

# Or inline detection (fallback):
ruby -e '
  gemfile = File.read("Gemfile") rescue ""
  lock = File.read("Gemfile.lock") rescue ""
  
  def gem_present?(content, name)
    content.match?(/^\s*gem\s+['\"]#{Regexp.escape(name)}['\"](?=\s*(?:,|#|$))/)
  end
  
  def lock_version(content, name)
    content[/^\s{4}#{Regexp.escape(name)} \(([^)]+)\)$/, 1]
  end

  puts "Ruby: #{RUBY_VERSION}"
  rails_version = lock_version(lock, "rails")
  puts "Rails: #{rails_version}" if rails_version

  {
    "Grape" => "grape",
    "Sidekiq" => "sidekiq",
    "Karafka" => "karafka",
    "Hotwire" => "hotwire-rails"
  }.each do |label, gem_name|
    next unless gem_present?(gemfile, gem_name)
    puts "#{label}: #{lock_version(lock, gem_name) || "detected"}"
  end

  puts "PostgreSQL: detected" if gem_present?(gemfile, "pg")
  puts "MySQL: detected" if gem_present?(gemfile, "mysql2")
  puts "Redis: detected" if gem_present?(gemfile, "redis") || gem_present?(gemfile, "redis-client")
'

# External tools (shell is fine here - simple commands)
command -v rtk &> /dev/null && echo "RTK: available"
command -v betterleaks &> /dev/null && echo "Betterleaks: available"
```

When building the injected header:

- omit Rails entirely when `RAILS_VERSION` is absent
- prefer `Grape 3.1.1`, `Sidekiq 6.5.12`, `Karafka 2.5.7`
- avoid degrading locked versions to `detected`

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
