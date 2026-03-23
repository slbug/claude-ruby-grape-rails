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
- Prefer raising errors for retry/backoff (Karafka handles retries automatically)
- Use `pause` for specific partition throttling scenarios, not general error handling
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
| `{OPTIONAL_STACK}` | Comma-prefixed extra versioned deps when available | , Karafka 2.5.7, Hotwire 2.0.0 |
| `{SIDEKIQ_SECTION}` | If sidekiq in Gemfile | Include Sidekiq section |
| `{HOTWIRE_SECTION}` | If hotwire-rails in Gemfile | Include Hotwire section |
| `{KARAFKA_SECTION}` | If karafka in Gemfile | Include Karafka section |
| `{RTK_SECTION}` | If rtk installed | Include RTK section |
| `{BETTERLEAKS_SECTION}` | If betterleaks installed | Include Betterleaks section |

## Detection Commands

Use the Ruby detection script (avoids fragile shell pipelines):

```bash
# Detect stack dependencies
ruby ${CLAUDE_PLUGIN_ROOT}/scripts/detect-stack.rb

# Prefer exact *_VERSION outputs from the script when composing the header.
# Only fall back to "detected" when the direct gem is present but no resolved
# version is available from Gemfile.lock.

# Or inline Ruby (if script unavailable):
ruby -e '
  gemfile = File.read("Gemfile") rescue ""
  lock = File.read("Gemfile.lock") rescue ""

  def gem_present?(content, name)
    content.match?(/^\s*gem\s+['\"]#{Regexp.escape(name)}['\"](?=\s*(?:,|#|$))/)
  end

  def lock_version(content, name)
    content[/^\s{4}#{Regexp.escape(name)} \(([^)]+)\)$/, 1]
  end

  {
    "rails" => "rails",
    "sidekiq" => "sidekiq",
    "hotwire" => "hotwire-rails",
    "karafka" => "karafka",
    "grape" => "grape"
  }.each do |label, gem_name|
    next unless gem_present?(gemfile, gem_name)
    puts "#{label}=#{lock_version(lock, gem_name) || "detected"}"
  end
'

# Version detection (via Gemfile.lock)
# Use exact gem-name matches only; never use loose /rails \((...)\)/ style regexes
# because they can falsely match gems such as rubocop-rails.
ruby -e 'lock = File.read("Gemfile.lock"); puts lock[/^\s{4}rails \(([^)]+)\)$/, 1] || "?"'
ruby -e 'lock = File.read("Gemfile.lock"); puts lock[/^\s{4}sidekiq \(([^)]+)\)$/, 1] || "?"'
ruby -e 'lock = File.read("Gemfile.lock"); puts lock[/^\s{4}grape \(([^)]+)\)$/, 1] || "?"'
ruby -e 'lock = File.read("Gemfile.lock"); puts lock[/^\s{4}karafka \(([^)]+)\)$/, 1] || "?"'

# RTK detection
command -v rtk &> /dev/null && echo "rtk"

# Betterleaks detection
command -v betterleaks &> /dev/null && echo "betterleaks"
```
