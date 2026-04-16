# Review Template Format

## Full Review Template

Write the consolidated review to `.claude/reviews/{review-slug}.md`.

Each reviewer also writes a per-agent artifact to:

- `.claude/reviews/{agent-slug}/{review-slug}-{datesuffix}.md`

````markdown
# Review: {Feature or Scope}

**Date**: {date}
**Complexity**: {Simple|Medium|Complex} ({count} files{, escalated: reason})
**Files Reviewed**: {count}
**Reviewers**: ruby-reviewer, testing-reviewer, security-analyzer, data-integrity-reviewer, migration-safety-reviewer

## Summary

| Severity | Count |
|----------|-------|
| Blockers | {n} |
| Warnings | {n} |
| Suggestions | {n} |

**Verdict**: PASS | PASS WITH WARNINGS | REQUIRES CHANGES | BLOCKED

## Blockers ({n})

### 1. {Issue Title}

**File**: {path}:{line}
**Reviewer**: {agent} | **Confidence**: {HIGH|MEDIUM|LOW}
**Issue**: {description}
**Why this matters**: {impact explanation}

**Current code**:

```ruby
bad_code
```

**Recommended approach**:

```ruby
good_code
```

---

### 2. {Issue Title}

...

## Warnings ({n})

### 1. {Issue Title}

**File**: {path}:{line}
**Reviewer**: {agent} | **Confidence**: {HIGH|MEDIUM|LOW}
**Issue**: {description}
**Recommendation**: {what to do}

---

## Suggestions ({n})

### 1. {Suggestion Title}

**File**: {path}
**Confidence**: {HIGH|MEDIUM|LOW}
**Suggestion**: {improvement idea}

````

## Verdict Decision Rules

| Verdict | Conditions |
|---------|-----------|
| **PASS** | No blockers, no warnings, suggestions only |
| **PASS WITH WARNINGS** | No blockers, warnings present but not test-coverage gaps |
| **REQUIRES CHANGES** | No Iron Law blockers, but test coverage gaps detected (see below) |
| **BLOCKED** | Iron Law violations or critical security/data issues |

### REQUIRES CHANGES Triggers

This verdict catches code that works but lacks adequate test coverage:

- New public methods with zero tests
- Removed tests without replacement coverage
- New controller actions without corresponding tests
- New Sidekiq jobs without `perform` tests
- New Turbo Stream routes without basic render tests

These are not blockers (code works) but should not merge without tests.

## Mandatory Summary Table

Every review MUST end with this at-a-glance table (even if only 1 finding):

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
| 1 | {title} | BLOCKER/WARNING/SUGGESTION | HIGH/MEDIUM/LOW | {agent} | {path}:{line} | Yes/Pre-existing |

**New?** column: "Yes" = finding on changed lines (this diff). "Pre-existing" = on unchanged code. Pre-existing issues appear in the report but do NOT affect the verdict.

**IMPORTANT**: The review template does NOT include task lists (`- [ ]`),
fix phases, or plan modifications. Review is findings-only. Task creation
belongs in `/rb:triage`.

After presenting the final review, suggest `/rb:triage` in chat if follow-up
planning is needed. Do not embed follow-up prompts or task-routing sections
inside the review artifact itself.
