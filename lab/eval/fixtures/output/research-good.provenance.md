---
claims:
  - id: c1
  - id: c2
  - id: c3
sources:
  - kind: primary
    url: https://github.com/sidekiq/sidekiq/wiki/Error-Handling
    supports: [c1, c2, c3]
  - kind: primary
    url: https://github.com/sidekiq/sidekiq/blob/main/Changes.md
    supports: [c1, c2, c3]
conflicts: []
---

# Provenance: sidekiq-retry-configuration.md

**Artifact**: `.claude/research/sidekiq-retry-configuration.md`
**Verified**: 3
**Unsupported**: 0
**Conflicts**: 0
**Weakly sourced**: 0
**Source Tiers**: T1:3 T2:0 T3:0

## Claim Log

1. [VERIFIED] "Sidekiq retry guidance should stay tied to current docs."
   - Evidence: <https://github.com/sidekiq/sidekiq/wiki/Error-Handling> [T1]
   - Notes: The wiki documents retry behavior and the supported configuration surface.

2. [VERIFIED] "Version-sensitive Sidekiq claims need explicit verification."
   - Evidence: <https://github.com/sidekiq/sidekiq/blob/main/Changes.md> [T1]
   - Notes: Changelog entries are the strongest source for versioned behavior changes.

3. [VERIFIED] "Older blog posts should not outrank current docs or changelogs."
   - Evidence: <https://github.com/sidekiq/sidekiq/blob/main/Changes.md> [T1]
   - Notes: Version-sensitive guidance should be anchored to current upstream documentation first.

## Required Fixes

- Keep older community posts as background only unless corroborated by T1/T2 sources.
