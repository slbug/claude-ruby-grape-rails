# Betterleaks Integration

Betterleaks is a secrets scanner that detects API keys, passwords, tokens, and other sensitive data in code.

## Installation

| Platform | Command |
|---|---|
| macOS | `brew install betterleaks` |
| Fedora Linux | `sudo dnf install betterleaks` |
| Docker | `docker pull ghcr.io/betterleaks/betterleaks:latest` |
| From source | `git clone https://github.com/betterleaks/betterleaks && cd betterleaks && make betterleaks` |

## Plugin Integration

### Automatic Detection

The plugin automatically detects betterleaks on session start and enables:

1. **Real-time scanning** - Files are scanned after write operations
2. **Command integration** - `/rb:secrets` command available
3. **Baseline support** - Track and ignore known/false-positive findings

### Commands

```
/rb:secrets                           # Scan current directory
/rb:secrets app/                      # Scan specific path
/rb:secrets --baseline leaks.json     # Use baseline file
/rb:secrets --validate                # Validate against live APIs
/rb:secrets --git                     # Scan git history
```

## Configuration

### Project-level (.betterleaks.toml)

Create in project root for custom rules:

```toml
title = "Project Betterleaks Config"

[extend]
useDefault = true

# Custom rule for project-specific secrets
[[rules]]
id = "internal-api-key"
description = "Internal API key format"
regex = '''internal-[a-zA-Z0-9]{40}'''
keywords = ["internal"]

# Ignore test fixtures
[[allowlists]]
description = "Test data"
paths = ['''spec/fixtures/.*''', '''test/fixtures/.*''']

# Ignore specific commits
[[allowlists]]
description = "Known test secrets"
commits = ["abc123", "def456"]
```

### Global Ignore (.betterleaksignore)

Create to ignore specific findings by fingerprint:

```
# Format: commit:file:rule:line
abc123:config/test.yml:generic-api-key:10
def456:.env.test:postgres-password:3
```

### Inline Ignore

Add comment to ignore specific lines:

```ruby
api_key = "sk_test_abc123" #betterleaks:allow
```

## Validation (Experimental)

Validate if detected secrets are live:

```bash
/rb:secrets --validate --experiments=validation
```

This makes HTTP requests to verify if API keys are active.

## CI/CD Integration

Add to your CI pipeline:

```yaml
# Example workflow file in your app repo: .github/workflows/secrets.yml
name: Secrets Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Scan for secrets
        uses: betterleaks/betterleaks-action@v1
        with:
          args: "git --baseline-path baseline.json"
```

## Best Practices

1. **Never commit `.env` files** - Add to `.gitignore` immediately
2. **Use Rails credentials** - `Rails.application.credentials`
3. **Rotate exposed keys** - If found, rotate immediately
4. **Baseline known issues** - Use baseline to track false positives
5. **Run before commits** - Make it part of pre-commit hooks

## Rules Reference

Betterleaks includes rules for:

- AWS credentials
- GitHub tokens
- Stripe keys
- Slack tokens
- Database URLs
- JWT tokens
- Private keys (RSA, DSA, EC)
- API keys (generic patterns)
- And 150+ more...

See full list: <https://github.com/betterleaks/betterleaks/blob/master/config/betterleaks.toml>
