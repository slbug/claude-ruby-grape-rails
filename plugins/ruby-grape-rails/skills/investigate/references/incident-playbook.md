# Incident Playbook

Apply when investigating live failure already shipped: Sentry / AppSignal
/ Honeybadger payload, user report, oncall page.

## 1. Triage payload

Extract before opening code:

- error class + message (exact text)
- top-N stack frames
- request context (method, path, user ID, params)
- environment + release tag

Reject "looks like X" without backtrace evidence.

### PII / secret redaction

Redact before persisting any payload excerpt to a durable artifact
(`.claude/solutions/...`, scratchpad, commit message):

| Source | Replacement |
|---|---|
| email | `<email>` |
| token / cookie / API key / password | `<redacted-secret>` |
| raw user identifier | opaque pseudonym (`<user-A>`) |
| arbitrary string params | `<param-name>=<redacted>` (drop unless load-bearing) |

Redact at extraction time. Never paste raw payloads into solution docs.
For load-bearing values (malformed token shape that triggers bug),
redact secret content but preserve structural pattern: `Bearer eyJ...<redacted>`.

## 2. Backtrace first

Read the full stack top-to-bottom. Locate the boundary where control
last left app code. That frame is the first place to probe.

## 3. Search prior solutions

```bash
grep -rn "<symptom-keyword>" .claude/solutions/
```

Read matching solution doc. Verify replacement strategy still applies
before re-using.

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

Cannot reproduce → no root cause. Stop. Gather more evidence from
production logs or escalate.

## 5. Regression-test-first fix

- Red test passes only after the fix
- Fix is the minimal diff (Iron Law 22)
- One concern per commit

## 6. Tidewave verify (when gem loaded)

Tidewave loaded:

- Query live routes / middleware / config; confirm production-shape
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

- Iron Law 18 — DON'T `rescue Exception` (or `::Exception`) in `begin/rescue` or Rails `rescue_from`. Bare `rescue` defaults to StandardError, not a Law 18 violation
- Iron Law 21 — VERIFY BEFORE CLAIMING DONE
- Iron Law 22 — SURGICAL CHANGES ONLY

## References

- `discipline.md` — investigation discipline rules
- `error-patterns.md` — Ruby/Rails error signatures
- `debug-commands.md` — command vocabulary
