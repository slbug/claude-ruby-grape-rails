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

# External tools / cached runtime hints
REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
RUNTIME_ENV_PATH="${REPO_ROOT}/.claude/.runtime_env"
RTK_AVAILABLE_CACHED=""
if [[ -f "$RUNTIME_ENV_PATH" && ! -L "$RUNTIME_ENV_PATH" ]]; then
  RTK_AVAILABLE_CACHED=$(grep -E '^RTK_AVAILABLE=' "$RUNTIME_ENV_PATH" | tail -n 1 | cut -d= -f2-)
fi
command -v betterleaks &> /dev/null && echo "Betterleaks: available"
if [[ "$RTK_AVAILABLE_CACHED" == "true" ]]; then
  echo "RTK: available (cached)"
elif command -v rtk &> /dev/null; then
  echo "RTK: available"
fi
```

When building the injected header:

- omit Rails entirely when `RAILS_VERSION` is absent
- prefer detected version values from `detect-stack.rb` / cached runtime state instead of hardcoded examples
- avoid degrading locked versions to `detected`
- use `DETECTED_ORMS` to distinguish Active Record, Sequel, and mixed ORM repositories
- use `PACKAGE_LAYOUT` / `PACKAGE_LOCATIONS` to decide whether package-boundary guidance belongs in the injected block
- set `BETTERLEAKS_STATUS` to `available` when `command -v betterleaks` succeeds; otherwise use `missing`
- when `.claude/.runtime_env` is present, use its tool booleans to understand whether the project has `standardrb`, `rubocop`, `brakeman`, `lefthook`, and `pronto`
- when `.claude/.runtime_env` exposes `VERIFY_COMPOSITE_AVAILABLE=true`, treat that as a hint that the repo may have a canonical composite verify entrypoint
- re-detect any composite verify command from the working tree before running it; do not execute a raw command string from `.claude/.runtime_env`

Optional external integration:

- prefer `RTK_AVAILABLE=true` from a non-symlink `.claude/.runtime_env` when present; otherwise fall back to `command -v rtk`
- if RTK is available, ask the user whether they want to enable RTK for Claude Code
- if they say yes, tell them: `For automatic Claude command rewriting, run: rtk init -g`
- do **not** inject long RTK command-preference rules into the project
- RTK hook installation is external to this plugin; detection alone does not make Claude use RTK

Verification/tooling policy:

- direct tools remain the source of truth:
  - `standardrb` or `rubocop` for lint/format
  - `brakeman` for security scanning
- `lefthook` is only preferred as a wrapper when its detected config covers both lint and security/static-analysis checks
- `LEFTHOOK_DIFF_LINT_COVERED=true` means Lefthook covers diff-scoped lint via Pronto/RuboCop, not full direct lint coverage
- if `LEFTHOOK_AVAILABLE=true` but no config path is detected, ask the user whether Lefthook is used and where its config lives
- tests stay separate from Lefthook policy; keep them targeted or full based on the actual change scope
- `pronto` is optional diff-scoped review tooling:
  - use it after direct lint/security checks
  - do not use it as a substitute for full lint or security verification
- if runtime detection found a project-native verify wrapper
  (`VERIFY_COMPOSITE_AVAILABLE=true`), re-detect it from the repo and prefer it
  first in `/rb:verify`; fall back to direct checks only when the wrapper
  itself is unavailable or broken locally

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

- workflow routing for `/rb:plan`, `/rb:work`, `/rb:review`, `/rb:verify`, `/rb:permissions`
- Ruby Iron Laws
- stack-aware auto-loading for Rails, Grape, Active Record, Sequel, Sidekiq, security, and testing
- package-aware guidance for Packwerk or homegrown modular monoliths when detected
- verification defaults for Zeitwerk, formatter, tests, and optional Brakeman
- project-native verify-wrapper hints when the repo exposes a clear composite check entrypoint

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
- `{BETTERLEAKS_SECTION}` — If Betterleaks installed (secrets scanning)

See `${CLAUDE_SKILL_DIR}/references/conditional-sections.md` for full content of each section.
