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

## Tool Selection Policy

- Read `${REPO_ROOT}/.claude/.runtime_env` when present and non-symlinked; use
  its tool booleans as the primary command-selection source of truth.
- Prefer direct tools as the source of truth:
  - `bundle exec standardrb` or `bundle exec rubocop`
  - `bundle exec brakeman`
- Use `lefthook run <hook>` only when cached runtime detection shows:
  - `LEFTHOOK_AVAILABLE=true`
  - `LEFTHOOK_CONFIG_PRESENT=true`
  - `LEFTHOOK_LINT_SECURITY_COVERED=true`
- If Lefthook is available but no config is detected, ask the user where the config lives before treating it as authoritative.
- `LEFTHOOK_DIFF_LINT_COVERED=true` means Lefthook covers diff-scoped Pronto/RuboCop review only; it does not replace full direct linting.
- Tests are separate from Lefthook policy and should stay targeted/full based on change scope.
- Treat `pronto` as an optional final diff-scoped pass:
  - run it after direct lint/security checks
  - do not use it as a substitute for StandardRB/RuboCop or Brakeman

When cached runtime state is available:

- `STANDARDRB_AVAILABLE=true` → prefer `bundle exec standardrb`
- else `RUBOCOP_AVAILABLE=true` → prefer `bundle exec rubocop`
- `BRAKEMAN_AVAILABLE=true` → run `bundle exec brakeman`
- `PRONTO_AVAILABLE=true` → allow optional final `bundle exec pronto run -c <base>`
- `LEFTHOOK_*` booleans control whether Lefthook is an acceptable wrapper, not whether direct checks disappear

## Verification Stack

```
┌─────────────────────────────────────────────────────────┐
│  VERIFICATION ORDER                                       │
├─────────────────────────────────────────────────────────┤
│  1. Zeitwerk Check     → File naming & autoloading      │
│  2. Lint               → StandardRB / RuboCop           │
│  3. Security           → Brakeman / static analysis     │
│  4. Tests              → RSpec/Minitest                 │
│  5. Type Check         → Sorbet/Steep (if present)      │
│  6. Database           → Pending migrations             │
│  7. Pronto (optional)  → Diff-scoped final pass         │
└─────────────────────────────────────────────────────────┘
```

### 1. Zeitwerk Check (full Rails apps)

```bash
bundle exec rails zeitwerk:check
```

Run this only when cached runtime state shows `FULL_RAILS_APP=true` or the repo
clearly has `bin/rails`.

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

#### StandardRB (preferred when `STANDARDRB_AVAILABLE=true`)

```bash
# Check only
bundle exec standardrb

# Auto-fix
bundle exec standardrb --fix

# Check specific files
bundle exec standardrb app/models/user.rb app/services/
```

#### RuboCop (use when `STANDARDRB_AVAILABLE!=true` and `RUBOCOP_AVAILABLE=true`)

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

If `LEFTHOOK_LINT_SECURITY_COVERED=true`, you may run the appropriate
`lefthook run <hook>` entrypoint instead of separate lint/security commands,
but only when the config clearly covers both categories.

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

If Lefthook is detected but only covers lint or only covers security/static
analysis, keep running the missing direct tool yourself.

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

### 7. Diff-Scoped Review (Optional Pronto)

Run this only after direct lint/security checks pass:

```bash
BASE_REF=$(git rev-parse --verify origin/main >/dev/null 2>&1 && echo origin/main || \
  git rev-parse --verify main >/dev/null 2>&1 && echo main || \
  git rev-parse --verify origin/master >/dev/null 2>&1 && echo origin/master || \
  git rev-parse --verify master >/dev/null 2>&1 && echo master)

[[ -n "$BASE_REF" ]] && bundle exec pronto run -c "$BASE_REF"
```

Use the first base ref that exists. Pronto is a last-step changed-files pass,
not a replacement for StandardRB/RuboCop or Brakeman.

## Verification Profiles

### Quick Check (CI)

```bash
#!/bin/bash
# .github/workflows/ruby.yml or similar

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
RUNTIME_ENV_FILE="$REPO_ROOT/.claude/.runtime_env"

runtime_flag() {
  local key="$1"
  [[ -f "$RUNTIME_ENV_FILE" && ! -L "$RUNTIME_ENV_FILE" ]] || return 0
  grep -E "^${key}=" "$RUNTIME_ENV_FILE" | tail -n 1 | cut -d= -f2-
}

gem_or_lock_has() {
  local gem_name="$1"
  grep -Eq "gem ['\"]${gem_name}['\"]|^[[:space:]]{4}${gem_name} " \
    "$REPO_ROOT/Gemfile" "$REPO_ROOT/Gemfile.lock" 2>/dev/null
}

gem_prefix_has() {
  local gem_prefix="$1"
  grep -Eq "gem ['\"]${gem_prefix}-|^[[:space:]]{4}${gem_prefix}-" \
    "$REPO_ROOT/Gemfile" "$REPO_ROOT/Gemfile.lock" 2>/dev/null
}

FULL_RAILS_APP=$(runtime_flag FULL_RAILS_APP)
STANDARDRB_AVAILABLE=$(runtime_flag STANDARDRB_AVAILABLE)
RUBOCOP_AVAILABLE=$(runtime_flag RUBOCOP_AVAILABLE)
BRAKEMAN_AVAILABLE=$(runtime_flag BRAKEMAN_AVAILABLE)
PRONTO_AVAILABLE=$(runtime_flag PRONTO_AVAILABLE)

if [[ ! -f "$RUNTIME_ENV_FILE" || -L "$RUNTIME_ENV_FILE" ]]; then
  echo "Runtime cache missing, falling back to repo detection."
fi

if [[ -z "$FULL_RAILS_APP" ]]; then
  if [[ -x "$REPO_ROOT/bin/rails" ]] || \
     [[ -f "$REPO_ROOT/config/application.rb" && -f "$REPO_ROOT/config/environment.rb" ]]; then
    FULL_RAILS_APP=true
  else
    FULL_RAILS_APP=false
  fi
fi

if [[ -z "$STANDARDRB_AVAILABLE" ]] && gem_or_lock_has standard; then
  STANDARDRB_AVAILABLE=true
fi

if [[ -z "$RUBOCOP_AVAILABLE" ]]; then
  if gem_or_lock_has rubocop || gem_prefix_has rubocop; then
    RUBOCOP_AVAILABLE=true
  fi
fi

if [[ -z "$BRAKEMAN_AVAILABLE" ]] && gem_or_lock_has brakeman; then
  BRAKEMAN_AVAILABLE=true
fi

if [[ -z "$PRONTO_AVAILABLE" ]]; then
  if gem_or_lock_has pronto || gem_prefix_has pronto; then
    PRONTO_AVAILABLE=true
  fi
fi

echo "=== Zeitwerk Check ==="
if [[ "$FULL_RAILS_APP" == "true" ]]; then
  bundle exec rails zeitwerk:check
fi

echo "=== Linting ==="
if [[ "$STANDARDRB_AVAILABLE" == "true" ]]; then
  bundle exec standardrb
elif [[ "$RUBOCOP_AVAILABLE" == "true" ]]; then
  bundle exec rubocop
fi

echo "=== Security ==="
if [[ "$BRAKEMAN_AVAILABLE" == "true" ]]; then
  bundle exec brakeman -q -w2 --no-pager
fi

echo "=== Tests ==="
if [[ -d "spec" ]]; then
  bundle exec rspec --format progress
elif [[ -d "test" ]]; then
  if [[ "$FULL_RAILS_APP" == "true" ]]; then
    bundle exec rails test
  else
    bundle exec rake test
  fi
else
  echo "No spec/ or test/ directory found, skipping tests."
fi

echo "=== Diff Review (optional) ==="
if [[ "$PRONTO_AVAILABLE" == "true" ]]; then
  BASE_REF=$(git rev-parse --verify origin/main >/dev/null 2>&1 && echo origin/main || \
    git rev-parse --verify main >/dev/null 2>&1 && echo main || \
    git rev-parse --verify origin/master >/dev/null 2>&1 && echo origin/master || \
    git rev-parse --verify master >/dev/null 2>&1 && echo master)
  [[ -n "$BASE_REF" ]] && bundle exec pronto run -c "$BASE_REF" || true
else
  echo "Pronto not available, skipping diff review."
fi
```

### Full Verification

```bash
#!/bin/bash
# Pre-commit or release check

set -e

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
RUNTIME_ENV_FILE="$REPO_ROOT/.claude/.runtime_env"

runtime_flag() {
  local key="$1"
  [[ -f "$RUNTIME_ENV_FILE" && ! -L "$RUNTIME_ENV_FILE" ]] || return 0
  grep -E "^${key}=" "$RUNTIME_ENV_FILE" | tail -n 1 | cut -d= -f2-
}

gem_or_lock_has() {
  local gem_name="$1"
  grep -Eq "gem ['\"]${gem_name}['\"]|^[[:space:]]{4}${gem_name} " \
    "$REPO_ROOT/Gemfile" "$REPO_ROOT/Gemfile.lock" 2>/dev/null
}

gem_prefix_has() {
  local gem_prefix="$1"
  grep -Eq "gem ['\"]${gem_prefix}-|^[[:space:]]{4}${gem_prefix}-" \
    "$REPO_ROOT/Gemfile" "$REPO_ROOT/Gemfile.lock" 2>/dev/null
}

FULL_RAILS_APP=$(runtime_flag FULL_RAILS_APP)
STANDARDRB_AVAILABLE=$(runtime_flag STANDARDRB_AVAILABLE)
RUBOCOP_AVAILABLE=$(runtime_flag RUBOCOP_AVAILABLE)
BRAKEMAN_AVAILABLE=$(runtime_flag BRAKEMAN_AVAILABLE)
PRONTO_AVAILABLE=$(runtime_flag PRONTO_AVAILABLE)

if [[ ! -f "$RUNTIME_ENV_FILE" || -L "$RUNTIME_ENV_FILE" ]]; then
  echo "Runtime cache missing, falling back to repo detection."
fi

if [[ -z "$FULL_RAILS_APP" ]]; then
  if [[ -x "$REPO_ROOT/bin/rails" ]] || \
     [[ -f "$REPO_ROOT/config/application.rb" && -f "$REPO_ROOT/config/environment.rb" ]]; then
    FULL_RAILS_APP=true
  else
    FULL_RAILS_APP=false
  fi
fi

if [[ -z "$STANDARDRB_AVAILABLE" ]] && gem_or_lock_has standard; then
  STANDARDRB_AVAILABLE=true
fi

if [[ -z "$RUBOCOP_AVAILABLE" ]]; then
  if gem_or_lock_has rubocop || gem_prefix_has rubocop; then
    RUBOCOP_AVAILABLE=true
  fi
fi

if [[ -z "$BRAKEMAN_AVAILABLE" ]] && gem_or_lock_has brakeman; then
  BRAKEMAN_AVAILABLE=true
fi

if [[ -z "$PRONTO_AVAILABLE" ]]; then
  if gem_or_lock_has pronto || gem_prefix_has pronto; then
    PRONTO_AVAILABLE=true
  fi
fi

echo "1/7 Zeitwerk Check..."
if [[ "$FULL_RAILS_APP" == "true" ]]; then
  bundle exec rails zeitwerk:check
fi

echo "2/7 Linting..."
if [[ "$STANDARDRB_AVAILABLE" == "true" ]]; then
  bundle exec standardrb --format progress
elif [[ "$RUBOCOP_AVAILABLE" == "true" ]]; then
  bundle exec rubocop
fi

echo "3/7 Security Scan..."
if [[ "$BRAKEMAN_AVAILABLE" == "true" ]]; then
  bundle exec brakeman -q --no-pager
fi

echo "4/7 Type Check..."
bundle exec srb tc 2>/dev/null || echo "No Sorbet configured"

echo "5/7 Database..."
if [[ "$FULL_RAILS_APP" == "true" ]]; then
  bundle exec rails db:migrate:status
else
  echo "Non-Rails project detected, skipping database migration status."
fi

echo "6/7 Tests..."
if [[ -d "spec" ]]; then
  bundle exec rspec --format documentation
elif [[ -d "test" ]]; then
  if [[ "$FULL_RAILS_APP" == "true" ]]; then
    bundle exec rails test
  else
    bundle exec rake test
  fi
else
  echo "No spec/ or test/ directory found, skipping tests."
fi

echo "7/7 Diff Review (optional)..."
if [[ "$PRONTO_AVAILABLE" == "true" ]]; then
  BASE_REF=$(git rev-parse --verify origin/main >/dev/null 2>&1 && echo origin/main || \
    git rev-parse --verify main >/dev/null 2>&1 && echo main || \
    git rev-parse --verify origin/master >/dev/null 2>&1 && echo origin/master || \
    git rev-parse --verify master >/dev/null 2>&1 && echo master)
  [[ -n "$BASE_REF" ]] && bundle exec pronto run -c "$BASE_REF" || true
else
  echo "Pronto not available, skipping diff review."
fi

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
| Pronto | Fix the changed-file issue, then rerun direct lint/security if needed |

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
| `bundle exec rails zeitwerk:check` | Verify autoloading for full Rails apps |
| `bundle exec standardrb` | Check style when StandardRB is configured |
| `bundle exec standardrb --fix` | Auto-fix style when StandardRB is configured |
| `bundle exec rubocop` | Check style when RuboCop is configured |
| `bundle exec brakeman` | Security scan when Brakeman is configured |
| `bundle exec pronto run -c <base>` | Diff-scoped final pass |
| `bundle exec rspec` | Run tests |
| `bundle exec rails test` | Run Minitest |
| `bundle exec rails db:migrate:status` | Check migrations |
