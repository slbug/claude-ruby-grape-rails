# Conditional Sections for Injectable Template

These sections are included in CLAUDE.md based on detected project dependencies.

## SIDEKIQ_SECTION

```markdown
**Sidekiq Specifics**:

- Workers MUST include `Sidekiq::Job`
- Use `sidekiq_options queue: :default, retry: 3`
- Enqueue only after commit using the active ORM's commit-safe mechanism
- Dead letter queue for permanent failures
- Monitor via Sidekiq Web UI
```

## SEQUEL_SECTION

```markdown
**Sequel Specifics**:

- Identify `Sequel::Model` and `Sequel.migration` files before applying Rails / Active Record patterns
- Prefer `DB.transaction` and Sequel transaction hooks for commit-safe Sidekiq enqueueing
- Do not generate `ActiveRecord::Migration[...]` classes inside Sequel packages
- Treat datasets, associations, and migrations as package-local when the repo mixes ORMs
```

## MIXED_ORM_SECTION

```markdown
**Mixed ORM Specifics**:

- This repo uses both Active Record and Sequel
- Before changing models, jobs, or migrations, identify which ORM owns the touched package
- Sidekiq enqueue-after-commit rules must follow the package's ORM, not a global Rails default
- Never assume all migrations in this repo are Active Record migrations
```

## HOTWIRE_SECTION

```markdown
**Hotwire/Turbo Specifics**:

- NEVER query DB in Turbo Stream responses
- Use `turbo_frame_tag` for partial updates
- Broadcast after commit: `after_create_commit -> { broadcast_prepend_to "posts" }`
- Pre-compute assigns before streams
```

## KARAFKA_SECTION

```markdown
**Karafka (Kafka) Specifics**:

- Consumers MUST be idempotent
- Handle message duplication gracefully
- Prefer raising errors for retry/backoff (Karafka handles retries automatically)
- Use `pause` for specific partition throttling scenarios, not general error handling
- Monitor lag via Karafka Web UI
```

## PACKWERK_SECTION

```markdown
**Modular Monolith / Packwerk Specifics**:

- Identify the owning package before changing code
- Respect package boundaries and public APIs
- Avoid proposing cross-package changes as if this were one flat Rails app
- If package ownership or stack differs across modules, ask before applying global guidance
```

## BETTERLEAKS_SECTION

```markdown
**Betterleaks (Secrets Scanning)**:

When reading logs or files that may contain PII/credentials, ALWAYS
pipe through `betterleaks stdin --redact=100` instead of `cat`:

```bash
betterleaks stdin --redact=100 < production.log
betterleaks stdin --redact=100 < .env
```

Before committing, scan with `/rb:secrets` or:

```bash
betterleaks git --redact=100          # Scan git history
betterleaks dir . --redact=100        # Scan directory
betterleaks dir app/ --validate       # Validate secrets against APIs
```

Install: `brew install betterleaks`

```

## Placeholder Substitution

| Placeholder | Source | Example |
|-------------|--------|---------|
| `{DATE}` | Current date | 2026-03-22 |
| `{RUBY_VERSION}` | `ruby --version` | 3.3.0 |
| `{RAILS_VERSION}` | Gemfile.lock | 7.1.3 |
| `{GRAPE_VERSION}` | Gemfile.lock | 2.0.0 |
| `{SIDEKIQ_VERSION}` | Gemfile.lock | 7.2.0 |
| `{OPTIONAL_STACK}` | Comma-prefixed extra versioned deps from detector output when available | , Karafka <detected>, Hotwire <detected> |
| `{SIDEKIQ_SECTION}` | If sidekiq in Gemfile | Include Sidekiq section |
| `{SEQUEL_SECTION}` | If Sequel detected | Include Sequel section |
| `{MIXED_ORM_SECTION}` | If Active Record and Sequel both detected | Include mixed ORM section |
| `{HOTWIRE_SECTION}` | If hotwire-rails in Gemfile | Include Hotwire section |
| `{KARAFKA_SECTION}` | If karafka in Gemfile | Include Karafka section |
| `{PACKWERK_SECTION}` | If Packwerk or modular layout detected | Include package/boundary section |
| `{BETTERLEAKS_SECTION}` | If betterleaks installed | Include Betterleaks section |
| `{BETTERLEAKS_STATUS}` | `command -v betterleaks` result | available / missing |
| `{PLUGIN_VERSION}` | `jq -r '.version // empty' "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json"` | 1.13.1 |

## Detection Commands

Use the Ruby detection script (avoids fragile shell pipelines):

```bash
${CLAUDE_PLUGIN_ROOT}/bin/detect-stack
command -v betterleaks &>/dev/null && echo "betterleaks"
```

Compose the header from `detect-stack` output:

- Prefer exact `*_VERSION` outputs from the script. Only fall back
  to `detected` when the direct gem is present but no resolved
  version is available from `Gemfile.lock`.
- Read `DETECTED_ORMS` / `PACKAGE_LAYOUT` / `PACKAGE_LOCATIONS`.
- If `PACKAGE_QUERY_NEEDED=true`, ask the user for module/package
  locations and stack details.

`detect-stack` is the only supported stack detector. Do NOT
recreate its logic inline. If it is missing or fails, stop and
surface that as a plugin/detection issue rather than guessing.
