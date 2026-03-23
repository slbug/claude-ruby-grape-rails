---
name: rb:init
description: Initialize the Ruby/Rails/Grape plugin in a project. Installs auto-activation rules into CLAUDE.md for complexity detection, workflow routing, Iron Laws, and Ruby stack auto-loading.
argument-hint: "[--update]"
effort: low
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
5. Read `DETECTED_ORMS`, `PACKAGE_LAYOUT`, `PACKAGE_LOCATIONS`, `HAS_PACKWERK`, and `PACKAGE_QUERY_NEEDED` from the detector before deciding what ORM/package guidance to inject.
6. If `PACKAGE_QUERY_NEEDED=true`, ask the user: `No Packwerk detected. Do you have something similar implemented? Provide modules/packages location and their stack/ORM.`
7. **Do not** reimplement stack detection inline in chat or ad-hoc Ruby snippets. `detect-stack.rb` is the source of truth.
8. If `detect-stack.rb` is missing or fails, STOP and explain that plugin stack detection is unavailable instead of inventing a fallback parser.

Use Ruby for detection (avoids fragile shell pipelines):

```bash
# Detect Ruby version and stack dependencies
ruby ${CLAUDE_PLUGIN_ROOT}/scripts/detect-stack.rb

# External tools (shell is fine here - simple commands)
command -v rtk &> /dev/null && echo "RTK: available"
command -v betterleaks &> /dev/null && echo "Betterleaks: available"
```

When building the injected header:

- omit Rails entirely when `RAILS_VERSION` is absent
- prefer `Grape 3.1.1`, `Sidekiq 6.5.12`, `Karafka 2.5.7`
- avoid degrading locked versions to `detected`
- use `DETECTED_ORMS` to distinguish Active Record, Sequel, and mixed ORM repositories
- use `PACKAGE_LAYOUT` / `PACKAGE_LOCATIONS` to decide whether package-boundary guidance belongs in the injected block

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
- stack-aware auto-loading for Rails, Grape, Active Record, Sequel, Sidekiq, security, and testing
- package-aware guidance for Packwerk or homegrown modular monoliths when detected
- verification defaults for Zeitwerk, formatter, tests, and optional Brakeman

## Template

Use `${CLAUDE_SKILL_DIR}/references/injectable-template.md` as the injected source of truth.

## Conditional Sections

Include based on detected stack and installed tools:

- `{SIDEKIQ_SECTION}` — If Sidekiq detected
- `{SEQUEL_SECTION}` — If Sequel detected
- `{MIXED_ORM_SECTION}` — If both Active Record and Sequel are detected
- `{HOTWIRE_SECTION}` — If Hotwire/Turbo detected
- `{KARAFKA_SECTION}` — If Karafka detected
- `{PACKWERK_SECTION}` — If Packwerk or modular monolith structure detected
- `{RTK_SECTION}` — If RTK installed (token optimization tool)
- `{BETTERLEAKS_SECTION}` — If Betterleaks installed (secrets scanning)

See `${CLAUDE_SKILL_DIR}/references/conditional-sections.md` for full content of each section.
