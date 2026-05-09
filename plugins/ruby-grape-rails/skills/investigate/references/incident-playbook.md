# Incident Playbook

Production-incident triage flow. Apply when investigating a live failure
that already shipped (Sentry/AppSignal/Honeybadger payload, user report,
oncall page).

## 1. Triage payload

Extract from the payload before opening any code:

- error class + message (exact text)
- top-N stack frames
- request context (method, path, user ID, params)
- environment + release tag

Never accept "looks like X" without backtrace evidence.

### PII / secret redaction

User IDs, params, request bodies, and stack-frame locals may contain
PII (emails, names, addresses), credentials (tokens, session cookies,
API keys), or business secrets. Before persisting any payload excerpt
to a durable artifact (`.claude/solutions/...`, scratchpad, commit
message), redact:

- email → `<email>`
- token / cookie / API key / password → `<redacted-secret>`
- raw user identifier → opaque pseudonym (`<user-A>`)
- arbitrary string params → `<param-name>=<redacted>` if value not
  load-bearing for the bug

Redact at extraction time. Never paste raw payloads into solution
docs. If a value IS load-bearing (e.g., specific malformed token
shape that triggers the bug), redact secret content while preserving
the structural pattern (`Bearer eyJ...<redacted>`).

## 2. Backtrace first

Read the full stack top-to-bottom. Locate the boundary where control
last left app code. That frame is the first place to probe.

## 3. Search prior solutions

```bash
grep -rn "<symptom-keyword>" .claude/solutions/
```

If a matching solution doc exists, read it. Verify replacement strategy
still applies before re-using.

## 4. Reproduce locally

Write a minimal failing spec before any code change:

```ruby
# spec/regression/issue_<id>_spec.rb
RSpec.describe "regression #<id>" do
  it "reproduces the failure from production" do
    # minimal setup matching production payload
    # assert exact failure occurs
  end
end
```

If you cannot reproduce, you do not have root cause. Stop. Gather more
evidence from production logs or escalate.

## 5. Regression-test-first fix

- Red test passes only after the fix
- Fix is the minimal diff (Iron Law 22)
- One concern per commit

## 6. Tidewave verify (when gem loaded)

If `tidewave` is loaded:

- Query live routes / middleware / config to confirm production-shape
- Use `rails runner` for one-off state introspection
- Confirm fix holds under real boot, not just test harness

## 7. Capture the solution

Update `.claude/solutions/<category>/<slug>.md`:

- symptom (exact error string)
- root cause (WHY, not WHAT)
- fix (code diff or summary)
- prevention rule (Iron Law / lint / test pattern)

Use `plugins/ruby-grape-rails/skills/compound/references/schema.md` +
`plugins/ruby-grape-rails/skills/compound/references/resolution-template.md`.

## Iron Laws referenced

- Iron Law 18 — DON'T RESCUE Exception
- Iron Law 21 — VERIFY BEFORE CLAIMING DONE
- Iron Law 22 — SURGICAL CHANGES ONLY

## References

- `discipline.md` — investigation discipline rules
- `error-patterns.md` — Ruby/Rails error signatures
- `debug-commands.md` — command vocabulary
