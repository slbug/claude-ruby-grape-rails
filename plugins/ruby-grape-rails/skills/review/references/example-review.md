# Example Review Output

```markdown
# Review: Magic Link Authentication

**Date**: 2024-01-15
**Files Reviewed**: 12
**Reviewers**: ruby-reviewer, testing-reviewer, security-analyzer

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 1 |
| Warnings | 2 |
| Suggestions | 3 |

**Verdict**: BLOCKED

## Blockers (1)

### 1. Magic Token Never Expires

**File**: app/models/magic_token.rb:45
**Reviewer**: security-analyzer
**Issue**: Magic tokens have no expiration, allowing indefinite reuse.
**Why this matters**: An attacker who obtains a token can use it forever.

**Current code**:

```ruby
def self.verify(token)
  find_by(token: token)
end
```

**Recommended approach**:

```ruby
def self.verify(token)
  where(token: token)
    .where("created_at > ?", 24.hours.ago)
    .first
end
```

## Warnings (2)

### 1. Missing Rate Limiting

**File**: app/controllers/magic_links_controller.rb
**Reviewer**: security-analyzer
**Issue**: No rate limiting on magic link requests
**Recommendation**: Add Rack::Attack or custom rate limiting

### 2. Test Coverage Gap

**File**: spec/models/magic_token_spec.rb
**Reviewer**: testing-reviewer
**Issue**: No test for expired token scenario
**Recommendation**: Add expiration test case

## At a Glance

| # | Finding | Severity | Reviewer | File | New? |
|---|---------|----------|----------|------|------|
| 1 | Magic token never expires | BLOCKER | security-analyzer | magic_token.rb:45 | Yes |
| 2 | Missing rate limiting | WARNING | security-analyzer | magic_links_controller.rb | Yes |
| 3 | No expired token test | WARNING | testing-reviewer | magic_token_spec.rb | Yes |

## Next Steps

How would you like to proceed?

- `/rb:plan` — Replan the fixes (for complex/architectural issues)
- `/rb:work .claude/plans/magic-link-auth/plan.md` — Fix directly
- I'll handle it myself

```
