---
name: security
description: "Use when applying Rails and Grape security patterns: authorization, SQL injection prevention, XSS, SSRF, secret handling, and secure background job workflows."
when_to_use: "Triggers: \"security\", \"authorization\", \"SQL injection\", \"XSS\", \"SSRF\", \"Brakeman\"."
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

## Defense in depth: CC sandbox network denylist

For infra-layer egress restriction (cloud metadata endpoints, known
exfiltration targets), use CC 2.1.113+ `sandbox.network.deniedDomains`. Runs
beneath plugin permission rules; applies to all Bash tool calls. See
`/rb:permissions` → "Network egress restriction" for the settings.json shape.

## References

| Need | Reference |
|---|---|
| betterleaks CLI integration + git-history scan | `${CLAUDE_SKILL_DIR}/references/betterleaks-integration.md` |
| Pundit/CanCanCan policies, password hashing, session auth | `${CLAUDE_SKILL_DIR}/references/authentication.md` |
| explicit authorization patterns + multi-tenant scopes | `${CLAUDE_SKILL_DIR}/references/authorization.md` |
| input validation, file-upload magic bytes, path traversal, XSS sanitization, SQL safety, command-injection prevention | `${CLAUDE_SKILL_DIR}/references/input-validation.md` |
| OAuth identity resolution + token refresh + multi-provider | `${CLAUDE_SKILL_DIR}/references/oauth-linking.md` |
| Rack::Attack rate limiting + composite keys + Redis limiter | `${CLAUDE_SKILL_DIR}/references/rate-limiting.md` |
| CSP, CSRF, HSTS, security headers, Brakeman + bundle-audit CI wiring | `${CLAUDE_SKILL_DIR}/references/security-headers.md` |
| SSRF, secrets management, supply chain, CORS, safe deserialization, file-upload content-type | `${CLAUDE_SKILL_DIR}/references/advanced-patterns.md` |
