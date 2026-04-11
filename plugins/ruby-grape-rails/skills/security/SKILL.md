---
name: security
description: "Rails and Grape security patterns: authorization, parameter shaping, SQL safety, XSS prevention, secret handling, SSRF/open redirects, and secure background job workflows."
user-invocable: false
effort: medium
paths:
  - "app/{policies,middleware,middlewares}/**"
  - "**/app/{policies,middleware,middlewares}/**"
  - "{packs,engines,components}/*/{policies,middleware,middlewares}/**"
  - "app/{packages,packs}/*/{policies,middleware,middlewares}/**"
---
# Security

## Iron Laws

1. Authorization must be explicit at every boundary.
2. Never interpolate untrusted input into SQL.
3. Never mark untrusted content as HTML safe.
4. Secrets come from environment or secure credentials, not source files.
5. Security-sensitive Sidekiq work must honor transaction boundaries.

## Secret Detection

Use `/rb:secrets` to scan for leaked credentials with betterleaks:

- `/rb:secrets` — Scan current directory
- `/rb:secrets --git` — Scan git history
- `/rb:secrets --validate` — Validate secrets against live APIs

Install betterleaks: `brew install betterleaks`

See `references/betterleaks-integration.md` for detailed configuration.
