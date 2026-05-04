# Example Review Output

````markdown
# Review: Magic Link Authentication

**Date**: 2026-04-15T14:23:00Z
**Complexity**: Medium (12 files, escalated: security-sensitive auth)
**Files Changed**: app/models/magic_token.rb, app/controllers/magic_links_controller.rb, spec/models/magic_token_spec.rb, db/migrate/20260415_create_magic_tokens.rb (+8 more)
**Reviewers**: ruby-reviewer, testing-reviewer, security-analyzer

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 BLOCKER / 0 WARNING / 1 SUGGESTION |
| testing-reviewer | artifact | 0 BLOCKER / 1 WARNING / 0 SUGGESTION |
| security-analyzer | stub-replaced | 1 BLOCKER / 1 WARNING / 0 SUGGESTION |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | PASS | PASS |
| testing-reviewer | PASS WITH WARNINGS | PASS WITH WARNINGS |
| security-analyzer | BLOCKED | BLOCKED |

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 1 |
| Warnings | 2 |
| Suggestions | 1 |

**Verdict**: BLOCKED

## Blockers (1)

### 1. Magic Token Never Expires

**File**: `app/models/magic_token.rb:45`
**Reviewer**: security-analyzer | **Confidence**: HIGH
**Issue**: Magic tokens have no expiration, allowing indefinite reuse.
**Why it matters**: An attacker who obtains a token can use it forever.

**Current**:

```ruby
def self.verify(token)
  find_by(token: token)
end
```

**Recommended**:

```ruby
def self.verify(token)
  where(token: token).where("created_at > ?", 24.hours.ago).first
end
```

## Warnings (2)

### 1. Missing Rate Limiting

**File**: `app/controllers/magic_links_controller.rb:18`
**Reviewer**: security-analyzer | **Confidence**: MEDIUM
**Issue**: No rate limiting on magic link requests.
**Recommendation**: Add Rack::Attack throttle or controller-level limit.

### 2. Test Coverage Gap on Expiration

**File**: `spec/models/magic_token_spec.rb:12`
**Reviewer**: testing-reviewer | **Confidence**: HIGH
**Issue**: No spec for the expired-token branch introduced by the new
`verify` scope.
**Recommendation**: Add `it "rejects expired tokens"` covering the
24h boundary.

## Suggestions (1)

### 1. Extract Magic-Token TTL Constant

**File**: `app/models/magic_token.rb`
**Confidence**: LOW
**Suggestion**: Replace inline `24.hours.ago` with `TTL = 24.hours`
constant + scope for reuse and test clarity.

## Pre-existing Issues (unchanged code)

- `app/models/user.rb:67` returns `nil` instead of raising on duplicate
  email creation; pre-existing, not introduced by this change.

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---|---|---|---|---|---|
| 1 | Magic token never expires | BLOCKER | HIGH | security-analyzer | `magic_token.rb:45` | Yes |
| 2 | Missing rate limiting | WARNING | MEDIUM | security-analyzer | `magic_links_controller.rb:18` | Yes |
| 3 | No expired-token spec | WARNING | HIGH | testing-reviewer | `magic_token_spec.rb:12` | Yes |
| 4 | Inline TTL literal | SUGGESTION | LOW | ruby-reviewer | `magic_token.rb` | Yes |
| 5 | Duplicate-email returns nil | BLOCKER | HIGH | ruby-reviewer | `user.rb:67` | Pre-existing |
````
