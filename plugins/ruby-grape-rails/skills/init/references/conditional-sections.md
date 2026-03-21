# Conditional Sections for Injectable Template

These sections are included in CLAUDE.md based on detected project dependencies.

## SIDEKIQ_SECTION

```markdown
**Sidekiq Specifics**:

- Workers MUST include `Sidekiq::Job`
- Use `sidekiq_options queue: :default, retry: 3`
- Dead letter queue for permanent failures
- Monitor via Sidekiq Web UI
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
- Use `pause` for transient errors, not `raise`
- Monitor lag via Karafka Web UI
```

## RTK_SECTION

```markdown
**RTK (Token Optimization)**:

If RTK is installed, PREFER `rtk` prefixed commands for better token efficiency:

| Instead of | Use | Savings |
|------------|-----|---------|
| `git status` | `rtk git status` | 80% |
| `git log` | `rtk git log` | 80% |
| `git diff` | `rtk git diff` | 75% |
| `ls` | `rtk ls` | 80% |
| `cat file` | `rtk read file` | 70% |
| `grep pattern` | `rtk grep pattern` | 80% |
| `bundle exec rspec` | `rtk test bundle exec rspec` | 90% |
| `docker ps` | `rtk docker ps` | 80% |

**Note:** RTK availability is detected at session start for informational purposes. You must manually invoke `rtk` commands - they are not automatically substituted.
```

## BETTERLEAKS_SECTION

```markdown
**Betterleaks (Secrets Scanning)**:

When reading logs or files that may contain PII/credentials, ALWAYS use:

```bash
# Instead of: cat production.log
betterleaks stdin --redact=100 < production.log

# Instead of: cat .env
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
| `{OPTIONAL_STACK}` | Detected optional deps | , Sidekiq, Hotwire, RTK |
| `{SIDEKIQ_SECTION}` | If sidekiq in Gemfile | Include Sidekiq section |
| `{HOTWIRE_SECTION}` | If hotwire-rails in Gemfile | Include Hotwire section |
| `{KARAFKA_SECTION}` | If karafka in Gemfile | Include Karafka section |
| `{RTK_SECTION}` | If rtk installed | Include RTK section |
| `{BETTERLEAKS_SECTION}` | If betterleaks installed | Include Betterleaks section |

## Detection Commands

```bash
# Ruby version
ruby --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "?"

# Rails version
ruby -e 'lock = File.exist?("Gemfile.lock") ? File.read("Gemfile.lock") : ""; puts lock[/rails \(([^)]+)\)/, 1] || "?"'

# Grape version
ruby -e 'lock = File.exist?("Gemfile.lock") ? File.read("Gemfile.lock") : ""; puts lock[/grape \(([^)]+)\)/, 1] || "?"'

# Sidekiq version
ruby -e 'lock = File.exist?("Gemfile.lock") ? File.read("Gemfile.lock") : ""; puts lock[/sidekiq \(([^)]+)\)/, 1] || "?"'

# Optional dependencies
grep -q 'gem ["'"'"]sidekiq["'"'"]' Gemfile && echo "sidekiq"
grep -q 'gem ["'"'"]hotwire-rails["'"'"]' Gemfile && echo "hotwire"
grep -q 'gem ["'"'"]karafka["'"'"]' Gemfile && echo "karafka"
grep -q 'gem ["'"'"]grape["'"'"]' Gemfile && echo "grape"

# RTK detection
command -v rtk &> /dev/null && echo "rtk"

# Betterleaks detection
command -v betterleaks &> /dev/null && echo "betterleaks"
```
