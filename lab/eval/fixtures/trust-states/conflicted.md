---
claims:
  - id: c1
sources:
  - kind: primary
    supports: [c1]
  - kind: primary
    supports: [c1]
conflicts:
  - claim: c1
    notes: Two primary sources disagree on the value.
---

# Provenance: conflicted fixture

**Artifact**: `lab/eval/fixtures/trust-states/conflicted.md`
**Verified**: 0
**Unsupported**: 0
**Conflicts**: 1
**Weakly sourced**: 0
**Source Tiers**: T1:2 T2:0 T3:0

## Claim Log

1. [CONFLICT] "Two primary sources disagree on the recommended value."
   - Evidence: <https://example.com/source-a> [T1]
   - Notes: Fixture for `conflicted` trust state.

## Required Fixes

- Resolve disagreement between source-a and source-b before relying on c1.
