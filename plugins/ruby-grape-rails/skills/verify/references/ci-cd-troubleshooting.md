# CI/CD Integration and Troubleshooting

CI/CD configuration and troubleshooting guides for Ruby/Rails verification.

## CI Integration

### GitHub Actions

```yaml
# .github/workflows/verify.yml
name: Verify

on: [push, pull_request]

jobs:
  verify:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Ruby
        uses: ruby/setup-ruby@v1
        with:
          ruby-version: '3.4'
          bundler-cache: true
      
      - name: Zeitwerk Check
        run: bundle exec rails zeitwerk:check
      
      - name: Lint
        run: bundle exec standardrb --format github
      
      - name: Security Scan
        run: bundle exec brakeman -q -w2 --no-pager
      
      - name: Setup Database
        run: |
          bundle exec rails db:create RAILS_ENV=test
          bundle exec rails db:schema:load RAILS_ENV=test
      
      - name: Run Tests
        run: bundle exec rspec --format progress
```

### GitLab CI

```yaml
# .gitlab-ci.yml
verify:
  stage: test
  script:
    - bundle exec rails zeitwerk:check
    - bundle exec standardrb
    - bundle exec brakeman -q -w2 --no-pager
    - bundle exec rspec --format progress
```

## Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit verification..."

# Stash unstaged changes
git stash -q --keep-index

# Run checks
if ! bundle exec standardrb --format quiet; then
  echo "❌ Linting failed. Run: bundle exec standardrb --fix"
  git stash pop -q
  exit 1
fi

if ! bundle exec rails zeitwerk:check > /dev/null 2>&1; then
  echo "❌ Zeitwerk check failed"
  git stash pop -q
  exit 1
fi

# Restore stashed changes
git stash pop -q

echo "✅ Pre-commit checks passed"
exit 0
```

## Environment-Specific Verification

### Development

```bash
# Quick sanity check
bundle exec standardrb --fix && bundle exec rspec spec/models/
```

### Staging

```bash
# Full verification before deploy
bundle exec rails zeitwerk:check && \
  bundle exec standardrb && \
  bundle exec brakeman && \
  bundle exec rspec
```

### Production Release

```bash
# Complete verification with documentation
bundle exec rails zeitwerk:check
bundle exec standardrb
bundle exec brakeman -o security-report.html
bundle exec rspec --format documentation
bundle exec rails db:migrate:status
```

## Troubleshooting

### Zeitwerk: File not found

```
expected file app/services/user_creator.rb to define constant UserCreator
```

**Causes**:

1. File defines wrong class name
2. File is in wrong directory
3. Module nesting mismatch

**Fix**:

```ruby
# app/services/user_creator.rb
# ❌ Wrong
class UserService::UserCreator

# ✅ Correct
class UserCreator
# or
module UserService
  class UserCreator
```

### RuboCop: Too many violations

```bash
# Run auto-fix first
bundle exec rubocop --autocorrect-all

# Then review remaining
bundle exec rubocop --format simple
```

### Brakeman: False positive

```ruby
# config/brakeman.ignore
{
  "ignored_warnings": [
    {
      "warning_type": "SQL Injection",
      "message": "Possible SQL injection",
      "file": "app/models/user.rb",
      "line": 45,
      "note": "False positive - using parameterized query"
    }
  ]
}
```

### Tests: Database issues

```bash
# Reset test database
RAILS_ENV=test bundle exec rails db:drop db:create db:schema:load

# Run specific failing test with debug
bundle exec rspec spec/models/user_spec.rb:45 --backtrace
```
