# CI/CD Integration and Troubleshooting

CI/CD configuration and troubleshooting guides for Ruby/Rails verification.

## CI Integration

### GitHub Actions

```yaml
# Example workflow file in your app repo: .github/workflows/verify.yml
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
# .husky/pre-commit.bash

echo "Running pre-commit verification..."

created_stash=false
if ! git diff --quiet -- .; then
  git stash push -q --keep-index -m pre-commit-verify
  created_stash=true
fi

restore_stash() {
  if [ "$created_stash" = true ]; then
    git stash pop -q
  fi
}
trap restore_stash EXIT

if ! bundle exec standardrb --format quiet; then
  echo "❌ Linting failed. Run: bundle exec standardrb --fix"
  exit 1
fi

if ! bundle exec rails zeitwerk:check >/dev/null 2>&1; then
  echo "❌ Zeitwerk check failed"
  exit 1
fi

trap - EXIT
restore_stash

echo "✅ Pre-commit checks passed"
exit 0
```

## Environment-Specific Verification

### Development — quick sanity check

```bash
bundle exec standardrb --fix && bundle exec rspec spec/models/
```

### Staging — full verification before deploy

```bash
bundle exec rails zeitwerk:check && \
  bundle exec standardrb && \
  bundle exec brakeman && \
  bundle exec rspec
```

### Production Release — complete verification with documentation

```bash
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

Run auto-fix first, then review remaining violations:

```bash
bundle exec rubocop --autocorrect-all
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

Reset the test database, then run a specific failing test with backtrace:

```bash
RAILS_ENV=test bundle exec rails db:drop db:create db:schema:load
bundle exec rspec spec/models/user_spec.rb:45 --backtrace
```
