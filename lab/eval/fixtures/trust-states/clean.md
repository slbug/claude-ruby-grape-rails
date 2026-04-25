---
claims:
  - id: c1
  - id: c2
sources:
  - kind: primary
    supports: [c1, c2]
  - kind: primary
    supports: [c1, c2]
conflicts: []
---

# Provenance: clean fixture

**Artifact**: `lab/eval/fixtures/trust-states/clean.md`
**Verified**: 2
**Unsupported**: 0
**Conflicts**: 0
**Weakly sourced**: 0
**Source Tiers**: T1:2 T2:0 T3:0

## Claim Log

1. [VERIFIED] "Two independent primary sources back claim 1."
   - Evidence: <https://example.com/spec> [T1]
   - Notes: Fixture for `clean` trust state.

2. [VERIFIED] "Two independent primary sources back claim 2."
   - Evidence: <https://example.com/spec> [T1]
   - Notes: Fixture for `clean` trust state.

## Required Fixes

- None
