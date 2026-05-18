# Review: New Reset-Password Endpoint

**Date**: 2026-04-18
**Complexity**: Simple (2 files)
**Files Changed**: app/controllers/passwords_controller.rb, config/routes.rb
**Reviewers**: ruby-reviewer, testing-reviewer

## Reviewer Coverage

| Reviewer | Recovery State | Findings |
|---|---|---|
| ruby-reviewer | artifact | 0 Blocker / 0 Warning / 0 Suggestion |
| testing-reviewer | artifact | 0 Blocker / 0 Warning / 0 Suggestion |

## Reviewer Verdicts

| Reviewer | Raw Verdict | Canonical |
|---|---|---|
| ruby-reviewer | PASS | PASS |
| testing-reviewer | REQUIRES CHANGES | REQUIRES CHANGES |

## Summary

| Severity | Count |
|----------|-------|
| Blockers | 0 |
| Warnings | 0 |
| Suggestions | 0 |

**Verdict**: REQUIRES CHANGES

## Test Coverage Gaps (2)

| # | Surface | File | Why uncovered | Suggested test |
|---|---------|------|---------------|----------------|
| 1 | `PasswordsController#create` | `app/controllers/passwords_controller.rb:8` | new public action; no spec exercises happy path | `spec/requests/passwords_controller_spec.rb` — assert reset email enqueued on valid email |
| 2 | `PasswordsController#create` rate-limit branch | `app/controllers/passwords_controller.rb:21` | new throttle path; no spec exercises 429 response | `spec/requests/passwords_controller_spec.rb` — assert 429 after threshold hits |

## At-a-Glance Finding Table

| # | Finding | Severity | Confidence | Reviewer | File | New? |
|---|---------|----------|------------|----------|------|------|
