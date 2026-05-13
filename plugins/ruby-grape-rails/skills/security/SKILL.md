---
name: security
description: "Rails/Grape security review: auth/role checks, injection risk, output sanitization, SSRF. Triggers: \"is this vulnerable\", \"SQL injection\", \"XSS\", \"Brakeman warning\", \"unauthorized access\". Do NOT use for: secret scans."
user-invocable: false
effort: medium
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

## Evidence Mode

Every finding MUST carry `evidence_mode`:

| Mode | Use when |
|---|---|
| `static-signal` | Grep / pattern match. Lowest trust. |
| `runtime-confirmed` | Reproduced via existing test OR read-only Tidewave introspection. |
| `configuration-risk` | Config-only issue (yml, env, initializer). |
| `requires-human-validation` | Threat-model / business-context input needed. |

Prefer `runtime-confirmed`. Refuse to emit findings without `evidence_mode`.

### `runtime-confirmed` is read-only

NEVER synthesize destructive code (DELETE/UPDATE/DROP/TRUNCATE/rm/mv,
new tests that mutate shared state, live network calls to non-mock
endpoints, config edits) to prove a finding. Allowed: existing tests,
read-only Tidewave queries, log inspection. If non-destructive
reproduction impossible → downgrade to `static-signal` or
`requires-human-validation`.

## Defense in depth: CC sandbox network denylist

For infra-layer egress restriction (cloud metadata endpoints, known
exfiltration targets), use CC 2.1.113+ `sandbox.network.deniedDomains`. Runs
beneath plugin permission rules; applies to all Bash tool calls. See
`/rb:permissions` → "Network egress restriction" for the settings.json shape.

## Gotchas

- Brakeman false-positive flood. Default Brakeman config flags many
  false positives. Triage by `evidence_mode`: `static-signal` Brakeman
  hits are LOWER priority than `runtime-confirmed` SQL injection in
  failing test.
- `evidence_mode` missing. Every finding MUST carry `evidence_mode`
  enum (defined in § Evidence Mode above). Refuse to emit findings without it.
- Pundit policy-scope omission. Authorize EVERY controller action
  (Iron Law 13). `before_action :authorize` alone is insufficient —
  verify per-action `policy_scope` or per-action `authorize` call.
- `html_safe` / `raw` on user input. Iron Law 14 violation. Search
  `\.html_safe|raw\(` in changed files; flag any with non-trusted source.

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
