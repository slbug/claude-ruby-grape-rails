---
name: rb:verify
description: Run the project verification stack for Ruby/Rails/Grape work. Detects the project toolchain and uses the strongest available checks. Validates autoloading, linting, tests, security, and migrations.
argument-hint: "[--quick|--full]"
effort: low
---
# Verify Ruby Work

Run verification in priority order, stopping at the first failure. Each step must pass before proceeding to the next.

## Iron Laws

1. **Never commit with failing tests.**
2. **Never skip security scans on public-facing code.**
3. **Always verify autoloading after structural changes.**
4. **Never ignore Zeitwerk check failures.**

## Verification Stack

```
┌─────────────────────────────────────────────────────────┐
│  VERIFICATION ORDER                                       │
├─────────────────────────────────────────────────────────┤
│  1. Zeitwerk Check     → File naming & autoloading      │
│  2. RuboCop/Standard   → Style & lint                   │
│  3. Brakeman           → Security scan                  │
│  4. Tests              → RSpec/Minitest                 │
│  5. Type Check         → Sorbet/Steep (if present)      │
│  6. Database           → Pending migrations             │
└─────────────────────────────────────────────────────────┘
```

### 1. Zeitwerk Check

```bash
bundle exec rails zeitwerk:check
```

**Purpose**: Verify all files can be autoloaded correctly.

**Pass**: All files load successfully  
**Fail**: File naming mismatch, syntax errors, circular dependencies

**Common Failures**:

```
❌ app/services/user_creator.rb defines UserCreator
   Expected: UserCreator
   Found:    UserService::UserCreator
   
   Fix: Rename module or file to match

❌ app/models/concerns/validatable.rb not found
   Expected: Validatable concern
   
   Fix: Move to app/models/concerns/validatable.rb
```

**No generic auto-fix flag**: `zeitwerk:check` reports the mismatch, but you
need to fix the file name, constant name, or inflector configuration yourself
and rerun the check.

### 2. Linting

#### StandardRB (preferred)

```bash
# Check only
bundle exec standardrb

# Auto-fix
bundle exec standardrb --fix

# Check specific files
bundle exec standardrb app/models/user.rb app/services/
```

#### RuboCop

```bash
# Check only
bundle exec rubocop

# Auto-fix safe corrections
bundle exec rubocop --autocorrect

# Auto-fix all (including unsafe)
bundle exec rubocop --autocorrect-all

# Check specific files
bundle exec rubocop app/models/user.rb

# Run specific cop
bundle exec rubocop --only Layout/LineLength
```

**Critical Cops** (never ignore):

- `Security/` - All security-related cops
- `Lint/` - Syntax and logic errors
- `Rails/` - Rails-specific issues

**Style Cops** (can defer):

- `Layout/` - Formatting (auto-fixable)
- `Style/` - Style preferences

### 3. Security Scan (Brakeman)

```bash
# Basic scan
bundle exec brakeman

# Quiet mode (errors only)
bundle exec brakeman -q

# Skip informational warnings
bundle exec brakeman -w2

# Output to file
bundle exec brakeman -o brakeman-report.html

# Ignore false positives (with reason)
bundle exec brakeman -I
```

**Never ignore**:

- SQL Injection
- Cross-Site Scripting (XSS)
- Mass Assignment
- Remote Code Execution
- File Access vulnerabilities

### 4. Tests

#### RSpec

```bash
# Full suite
bundle exec rspec

# Fail fast (stop on first failure)
bundle exec rspec --fail-fast

# Specific files
bundle exec rspec spec/models/user_spec.rb

# Specific line
bundle exec rspec spec/models/user_spec.rb:45

# Parallel (with parallel_tests gem)
bundle exec parallel_rspec spec/
```

#### Minitest

```bash
# Full suite
bundle exec rails test

# Fail fast
bundle exec rails test --fail-fast

# Specific files
bundle exec rails test test/models/user_test.rb

# Specific line
bundle exec rails test test/models/user_test.rb:45

# System tests only
bundle exec rails test:system
```

#### Test Selection

Run tests based on what changed:

```bash
# If model changed → Run model tests
bundle exec rspec spec/models/

# If controller changed → Run controller + request tests  
bundle exec rspec spec/controllers/ spec/requests/

# If migration changed → No tests needed, but verify migration
bundle exec rails db:migrate:status

# If gem changed → Full suite
bundle exec rspec
```

### 5. Type Checking (if present)

#### Sorbet

```bash
# Check types
bundle exec srb tc

# Check with strictness suggestions
bundle exec srb tc --suggest-typed
```

#### Steep

```bash
bundle exec steep check
```

#### RBS

```bash
# Validate type signatures
bundle exec rbs validate
```

### 6. Database Verification

```bash
# Check pending migrations
bundle exec rails db:migrate:status

# Verify schema is up to date
bundle exec rails db:migrate RAILS_ENV=test
bundle exec rails db:schema:dump

# Check for schema conflicts
git diff db/schema.rb
```

## Verification Profiles

### Quick Check (CI)

```bash
#!/bin/bash
# .github/workflows/ruby.yml or similar

set -e

echo "=== Zeitwerk Check ==="
bundle exec rails zeitwerk:check

echo "=== Linting ==="
bundle exec standardrb

echo "=== Security ==="
bundle exec brakeman -q -w2 --no-pager

echo "=== Tests ==="
bundle exec rspec --format progress
```

### Full Verification

```bash
#!/bin/bash
# Pre-commit or release check

set -e

echo "1/6 Zeitwerk Check..."
bundle exec rails zeitwerk:check

echo "2/6 Linting..."
bundle exec standardrb --format progress

echo "3/6 Security Scan..."
bundle exec brakeman -q --no-pager

echo "4/6 Type Check..."
bundle exec srb tc 2>/dev/null || echo "No Sorbet configured"

echo "5/6 Database..."
bundle exec rails db:migrate:status

echo "6/6 Tests..."
bundle exec rspec --format documentation

echo "✅ All checks passed!"
```

### Fast Feedback (Development)

```bash
# While iterating on code - skip heavy checks
bundle exec standardrb --fix && \
  bundle exec rspec spec/models/user_spec.rb
```

## Output Format

### Success

```
═══════════════════════════════════════════════════════════
                    VERIFICATION PASSED
═══════════════════════════════════════════════════════════

  ✅ Zeitwerk          All files load correctly
  ✅ StandardRB        No style violations
  ✅ Brakeman          No security issues
  ✅ RSpec             156 examples, 0 failures
  ⏭️  Sorbet           Not configured
  ✅ Database          No pending migrations

───────────────────────────────────────────────────────────
Time: 12.4 seconds
───────────────────────────────────────────────────────────
```

### Failure

```
═══════════════════════════════════════════════════════════
                    VERIFICATION FAILED
═══════════════════════════════════════════════════════════

  ✅ Zeitwerk          All files load correctly
  ❌ StandardRB        3 violations found
  ⏭️  Brakeman         Skipped (previous failure)
  ⏭️  RSpec            Skipped (previous failure)

───────────────────────────────────────────────────────────
StandardRB Failures:
───────────────────────────────────────────────────────────

app/models/user.rb:45:81: Layout/LineLength: Line is too long
app/services/order_creator.rb:12:3: Style/Documentation: Missing class comment  
app/controllers/orders_controller.rb:34:5: Rails/Output: Do not write to stdout

───────────────────────────────────────────────────────────
Next Step:
───────────────────────────────────────────────────────────
Run: bundle exec standardrb --fix

Or fix manually and re-run: /rb:verify
───────────────────────────────────────────────────────────
```

## Failure Handling

### Step 1: Identify the Issue

```bash
# Get detailed output
bundle exec rspec --format documentation spec/failing_spec.rb

# Run with backtrace
bundle exec rspec --backtrace spec/failing_spec.rb
```

### Step 2: Fix Strategy

| Check | Common Fix |
|-------|-----------|
| Zeitwerk | Fix file naming or module nesting |
| Lint | Run auto-fix: `standardrb --fix` |
| Security | Address vulnerability or add to ignore list with reason |
| Tests | Fix failing test or implementation |
| Types | Add/update type signatures |

### Step 3: Re-verify

```bash
# After fix, re-run just that check
bundle exec standardrb

# Then full verification
/rb:verify
```

## CI Integration & Troubleshooting

See: [references/ci-cd-troubleshooting.md](references/ci-cd-troubleshooting.md) — GitHub Actions, GitLab CI, pre-commit hooks, and troubleshooting guides

## Best Practices

1. **Run verification before every commit** (use pre-commit hook)
2. **Never skip security scans** on production-bound code
3. **Fix linting issues immediately** - they're usually auto-fixable
4. **Keep tests fast** - aim for < 1 minute for unit tests
5. **Use parallel testing** for large suites
6. **Document ignored warnings** with reasons
7. **Update ignore lists** when fixing real issues
8. **Run full verification** before PR creation

## Commands Summary

| Command | Purpose |
|---------|---------|
| `/rb:verify` | Run full verification stack |
| `bundle exec rails zeitwerk:check` | Verify autoloading |
| `bundle exec standardrb` | Check style |
| `bundle exec standardrb --fix` | Auto-fix style |
| `bundle exec brakeman` | Security scan |
| `bundle exec rspec` | Run tests |
| `bundle exec rails test` | Run Minitest |
| `bundle exec rails db:migrate:status` | Check migrations |
