---
name: rb:quick
description: "Making trivial one-line fixes, typos, and tiny config changes in a Ruby/Rails/Grape codebase. Skips planning ceremony: inspect, fix, verify. For obvious changes under ~20 lines."
argument-hint: <task>
effort: low
disable-model-invocation: true
---
# Quick Path

Use when the change is small, local, and low risk.

Still do three things:

1. inspect the existing code path first
2. implement directly
3. verify with the narrowest correct command set

## Related — invoke manually if needed

<!-- BEGIN-GENERATED related-footer -->
- Adjacent debt noticed but out of scope → `/rb:techdebt` (tech-debt logging)
<!-- END-GENERATED related-footer -->
