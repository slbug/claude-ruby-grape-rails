---
name: rb:secrets
description: Scan code for leaked secrets, API keys, and credentials using betterleaks. Use before committing to check for accidentally exposed passwords, tokens, or sensitive data.
argument-hint: "[path] [--baseline FILE] [--validate]"
effort: medium
---
# Secrets Scan

Detect leaked secrets in your codebase using betterleaks.

## Requirements

Requires betterleaks to be installed:

- macOS: `brew install betterleaks`
- Linux: `sudo dnf install betterleaks`
- Or download from the betterleaks releases page

## Usage

```
/rb:secrets                           # Scan current directory
/rb:secrets app/                      # Scan specific path
/rb:secrets --baseline leaks.json     # Use baseline to ignore known issues
/rb:secrets --validate                # Validate secrets against live APIs
/rb:secrets --git                     # Scan git history
```

## What It Scans

- API keys (GitHub, AWS, Stripe, etc.)
- Database connection strings
- Passwords and tokens
- Private keys
- Environment files (.env)
- Configuration files

## Iron Laws

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use Rails credentials** - `Rails.application.credentials`
3. **No secrets in code** - Use environment variables
4. **Rotate exposed keys immediately** - If found, rotate them

## Output

Returns findings with severity:

```
## Secrets Scan Results

### Critical
- config/database.yml: Contains production password
- .env.staging: AWS access key exposed

### High
- app/services/stripe.rb: Hardcoded API key

### Recommendations
- Move secrets to Rails credentials
- Add .env* to .gitignore
- Rotate exposed API keys
```

## Configuration

Create `.betterleaks.toml` in project root for custom rules:

```toml
[[rules]]
id = "custom-api-key"
description = "Custom API key pattern"
regex = '''api-key-[a-zA-Z0-9]{32}'''
keywords = ["api-key"]

[[allowlists]]
description = "Test fixtures"
paths = ['''test/fixtures/.*''']
```
