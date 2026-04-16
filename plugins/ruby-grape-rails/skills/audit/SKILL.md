---
name: rb:audit
description: "Use when you need a broad project-wide audit of a Ruby/Rails/Grape codebase covering architecture, security, performance, testing, and operational risk."
when_to_use: "Triggers: \"audit the project\", \"codebase health check\", \"architecture review\", \"security audit\", \"project-wide assessment\". Does NOT handle: reviewing individual PRs or diffs, fixing issues, running tests."
effort: max
---
# Audit

Review five areas:

- boundaries and code ownership
- security and auth surfaces
- data integrity and query quality
- test depth and flake risk
- deploy/runtime readiness
