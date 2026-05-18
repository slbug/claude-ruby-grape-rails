# Example Full Cycle Run

## Magic Link Authentication

```
$ /rb:full Add magic link authentication

[INITIALIZING] Creating feature branch: feature/magic-link-auth
[DISCOVERING] Scanning codebase for patterns...
  Complexity: High — security-critical, new auth mechanism
  User choice: "research it"

[PLANNING] Spawning 4 research agents (comprehensive)...
  ✓ web-researcher: Found 5 relevant discussions
  ✓ ruby-gem-researcher: Confirmed ActionMailer (Rails built-in; multipart HTML+text out of box) sufficient — no extra mailer gem needed
  ✓ rails-patterns-analyst: Identified existing auth patterns
  ✓ security-analyzer: Reviewed token security patterns
[PLANNING] Creating implementation plan...
  Phase 1: Token Schema (3 tasks)
  Phase 2: Authentication Service (4 tasks)
  Phase 3: Hotwire/Turbo Components (5 tasks)
  Phase 4: Tests (4 tasks)
[PLANNING] Written: .claude/plans/magic-link-auth/plan.md

[WORKING] Phase 1: Token Schema
  ✓ Task 1/3: [P1-T1][active record] Create magic_tokens migration
  ✓ Task 2/3: [P1-T2][active record] Add indexes
  ✓ Task 3/3: [P1-T3][active record] Create MagicToken model
[WORKING] Phase 1 complete, committed

[WORKING] Phase 2: Authentication Service
  ✓ Task 1/4: [P2-T1][direct] Add MagicLinkService PORO
  ✓ Task 2/4: [P2-T2][direct] Implement MagicLinkService#issue
  ✗ Task 3/4: [P2-T3][direct] Implement MagicLinkService#verify (retry 1/3)
  ✓ Task 3/4: [P2-T3][direct] Implement MagicLinkService#verify
  ✓ Task 4/4: [P2-T4][sidekiq] Add MagicLinkMailerJob
[WORKING] Phase 2 complete, committed

[WORKING] Phase 3: Hotwire/Turbo Components
  ✓ Task 1/5: [P3-T1][hotwire] Add MagicLinksController#new with Turbo Frame
  ✓ Task 2/5: [P3-T2][hotwire] Add MagicLinksController#verify with redirect
  ✓ Task 3/5: [P3-T3][direct] Add routes
  ✓ Task 4/5: [P3-T4][direct] ActionMailer template (HTML + text)
  ✓ Task 5/5: [P3-T5][hotwire] Turbo Stream flash partial
[WORKING] Phase 3 complete, committed

[WORKING] Phase 4: Tests
  ✓ Task 1/4: [P4-T1][test] Service specs (issue + verify happy paths)
  ✓ Task 2/4: [P4-T2][test] Request specs for MagicLinksController
  ✓ Task 3/4: [P4-T3][test] Integration spec end-to-end
  ✓ Task 4/4: [P4-T4][test] Mailer + Sidekiq job specs
[WORKING] Phase 4 complete, committed

[VERIFYING] /rb:verify --full
  ✓ Zeitwerk autoload check
  ✓ Lint / formatter
  ✓ Unit + request specs (all green)
  ✓ Brakeman (no findings)
  ✓ Migration safety scan
[VERIFYING] All gates passed

[REVIEWING] Spawning 4 review agents...
  ✓ ruby-reviewer: PASS (2 Suggestions noted)
  ✓ testing-reviewer: PASS
  ✓ security-analyzer: PASS (1 Suggestion: token expiry)
  ✓ verification-runner: All tests pass

[REVIEWING] Synthesized **Verdict**: PASS
            (no NEW Blockers, no Warnings introduced; 3 Suggestions noted)
            → continue to COMPOUNDING (no autonomous re-work loop)

[COMPOUNDING] Captured: "Magic link tokens should expire within 24 hours"

## Feature Complete

**Feature**: Magic link authentication
**Duration**: ~15 minutes
**Files Modified**: 12
**Tests Added**: 8

<promise>DONE</promise>
```
