---
claims:
  - id: c1
sources:
  - kind: primary
    url: app/controllers/passwords_controller.rb:8
    supports: [c1]
  - kind: primary
    url: app/controllers/passwords_controller.rb:21
    supports: [c1]
conflicts: []
---

# Provenance: new-reset-password-endpoint-review.md

**Artifact**: `.claude/reviews/new-reset-password-endpoint-review-20260418-100000.md`
**Verified**: 1
**Unsupported**: 0
**Conflicts**: 0
**Weakly sourced**: 0
**Source Tiers**: T1:0 T2:0 T3:0

## Claim Log

1. [VERIFIED] "New PasswordsController#create action is unspecified by any spec in this diff."
   - Evidence: app/controllers/passwords_controller.rb:8
   - Notes: Two new public surfaces introduced; neither has a spec target in the diff.

## Required Fixes

- Test coverage for `PasswordsController#create` happy path and 429 throttle branch (per `## Test Coverage Gaps` section in the consolidated review).
